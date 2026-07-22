from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from jmag_skill.executor.adapters.mock_jmag import MockJmagAdapter
from jmag_skill.executor.adapters.mock_scheduler import MockScheduler
from jmag_skill.executor.spec_loader import load_design_spec
from jmag_skill.executor.spec_resolver import resolve_design_spec
from jmag_skill.offline.materials import MaterialSelectionRequest, select_materials
from jmag_skill.offline.optimization import (
    build_optimization_manifest,
    generate_doe_cases,
)
from jmag_skill.offline.report import generate_design_report
from jmag_skill.offline.results import (
    normalize_result_metrics,
    run_physical_checks,
)
from jmag_skill.offline.sizing import SizingRequest, estimate_initial_dimensions
from jmag_skill.cli import main


ROOT = Path(__file__).parents[2]
SPEC = resolve_design_spec(
    load_design_spec(ROOT / "examples" / "design_specs" / "design_spec.yaml")
)


class OfflineCapabilityTests(unittest.TestCase):
    def test_execute_offline_cli_produces_complete_bundle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_directory = Path(temp_dir) / "offline-run"
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "execute-offline",
                        str(ROOT / "examples" / "design_specs" / "design_spec.yaml"),
                        "--run-directory",
                        str(run_directory),
                        "--maximum-cases",
                        "9",
                        "--submit-mock-job",
                    ]
                )

            self.assertEqual(exit_code, 0)
            for relative_path in (
                "result_bundle.json",
                "sizing_candidate.json",
                "material_candidates.json",
                "optimization_manifest.json",
                "doe_cases.json",
                "report/design_report.md",
                "scheduler/mock_job.json",
            ):
                self.assertTrue((run_directory / relative_path).is_file())

    def test_offline_cli_can_size_and_prepare_optimization(self):
        sizing_output = StringIO()
        with redirect_stdout(sizing_output):
            sizing_exit = main(
                [
                    "size-design",
                    "--rated-power-kw",
                    "110",
                    "--rated-speed-rpm",
                    "3000",
                ]
            )
        self.assertEqual(sizing_exit, 0)
        self.assertIn("specific_torque_volume_heuristic", sizing_output.getvalue())

        optimization_output = StringIO()
        with redirect_stdout(optimization_output):
            optimization_exit = main(
                [
                    "prepare-optimization",
                    str(ROOT / "examples" / "design_specs" / "design_spec.yaml"),
                    "--maximum-cases",
                    "9",
                ]
            )
        self.assertEqual(optimization_exit, 0)
        self.assertIn('"status": "offline_prepared"', optimization_output.getvalue())

    def test_report_cli_builds_report_from_a_mock_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_directory = Path(temp_dir) / "run"
            from jmag_skill.executor.workflow import execute_design

            execute_design(
                SPEC,
                MockJmagAdapter(),
                run_directory,
                input_spec_path=ROOT / "examples" / "design_specs" / "design_spec.yaml",
            )
            report_exit = main(["generate-report", str(run_directory)])

            self.assertEqual(report_exit, 0)
            self.assertTrue((run_directory / "report" / "design_report.md").is_file())

    def test_mock_scheduler_cli_submits_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "optimization.json"
            manifest.write_text(json.dumps({"maximum_cases": 2}), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "submit-mock-job",
                        str(manifest),
                        "--storage-directory",
                        str(root / "jobs"),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("mock-", output.getvalue())

    def test_result_normalization_adds_power_efficiency_and_checks(self):
        raw_metrics = {
            "average_torque": {
                "status": "available",
                "value": 350.0,
                "unit": "N*m",
                "source": "MockJmagAdapter.fixed_fixture",
            },
            "copper_loss": {"status": "available", "value": 4200.0, "unit": "W"},
            "iron_loss": {"status": "available", "value": 1800.0, "unit": "W"},
            "magnet_loss": {"status": "available", "value": 120.0, "unit": "W"},
        }

        normalized = normalize_result_metrics(SPEC, raw_metrics)
        checks = run_physical_checks(normalized)

        self.assertAlmostEqual(normalized["derived_metrics"]["mechanical_power"]["value"], 109955.7429, places=3)
        self.assertGreater(normalized["derived_metrics"]["efficiency"]["value"], 0.94)
        self.assertEqual(checks["status"], "passed")
        self.assertTrue(all(item["status"] == "passed" for item in checks["checks"]))

    def test_physical_checks_report_negative_loss_without_hiding_it(self):
        normalized = {
            "metrics": {
                "average_torque": {"status": "available", "value": 350.0, "unit": "N*m"},
                "copper_loss": {"status": "available", "value": -1.0, "unit": "W"},
            },
            "derived_metrics": {},
        }

        checks = run_physical_checks(normalized)

        self.assertEqual(checks["status"], "failed")
        self.assertIn("copper_loss_nonnegative", {item["name"] for item in checks["checks"]})

    def test_sizing_candidate_exposes_assumptions(self):
        candidate = estimate_initial_dimensions(
            SizingRequest(
                rated_power_kw=110.0,
                rated_speed_rpm=3000.0,
                specific_torque_nm_per_litre=20.0,
                aspect_ratio_length_to_diameter=0.6,
            )
        )

        self.assertAlmostEqual(candidate["rated_torque_nm"], 350.1667, places=3)
        self.assertGreater(candidate["active_volume_l"], 17.0)
        self.assertIn("assumptions", candidate)
        self.assertEqual(candidate["method"], "specific_torque_volume_heuristic")

    def test_material_selection_filters_temperature_and_keeps_cost_source(self):
        selected = select_materials(
            MaterialSelectionRequest(
                family="magnet",
                operating_temperature_c=160.0,
                maximum_cost_per_kg=120.0,
            )
        )

        self.assertTrue(selected)
        self.assertTrue(all(item["max_operating_temperature_c"] >= 160.0 for item in selected))
        self.assertTrue(all("cost_source" in item for item in selected))
        self.assertTrue(all("source" in item for item in selected))

    def test_optimization_manifest_and_doe_are_deterministic_and_bounded(self):
        variables = [
            {"name": "magnet_thickness_mm", "min": 3.0, "max": 7.0, "levels": 3, "unit": "mm"},
            {"name": "magnet_width_mm", "min": 18.0, "max": 22.0, "levels": 2, "unit": "mm"},
        ]
        manifest = build_optimization_manifest(
            variables=variables,
            objectives=[{"metric": "efficiency", "direction": "maximize"}],
            constraints=[{"metric": "average_torque", "operator": ">=", "value": 350.0}],
            maximum_cases=10,
        )
        cases = generate_doe_cases(manifest)

        self.assertEqual(manifest["estimated_cases"], 6)
        self.assertEqual(len(cases), 6)
        self.assertEqual(cases[0]["case_id"], "case_001")
        self.assertEqual(cases, generate_doe_cases(manifest))

    def test_mock_components_record_intended_jmag_capabilities(self):
        record = MockJmagAdapter().capability_record()

        self.assertEqual(record["evidence_status"], "mock_only")
        self.assertIn("create_geometry_editor", record["geometry"]["intended_jmag_functions"])
        self.assertIn("configure_magnetic_transient_study", record["study"]["intended_jmag_functions"])
        self.assertIn("extract_torque_and_losses", record["results"]["intended_jmag_functions"])

    def test_mock_scheduler_persists_job_lifecycle_and_capability_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            scheduler = MockScheduler(Path(temp_dir))
            job_id = scheduler.submit({"workflow": "baseline", "maximum_cases": 2})
            self.assertEqual(scheduler.status(job_id)["status"], "queued")
            completed = scheduler.advance(job_id)

            self.assertEqual(completed["status"], "completed")
            self.assertTrue((Path(temp_dir) / f"{job_id}.json").is_file())
            self.assertEqual(scheduler.capability_record()["evidence_status"], "mock_only")

    def test_report_contains_traceability_and_mock_boundary(self):
        normalized = normalize_result_metrics(
            SPEC,
            MockJmagAdapter().extract_results(SPEC, SPEC["outputs"]),
        )
        normalized["validation"] = run_physical_checks(normalized)
        sizing = estimate_initial_dimensions(
            SizingRequest(rated_power_kw=110.0, rated_speed_rpm=3000.0)
        )
        materials = select_materials(
            MaterialSelectionRequest(family="magnet", operating_temperature_c=140.0)
        )
        optimization = build_optimization_manifest(
            variables=[{"name": "magnet_thickness_mm", "min": 3.0, "max": 7.0, "levels": 2, "unit": "mm"}],
            objectives=[{"metric": "efficiency", "direction": "maximize"}],
            constraints=[],
            maximum_cases=4,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "design_report.md"
            generate_design_report(SPEC, normalized, output, sizing, materials, optimization)
            text = output.read_text(encoding="utf-8")

        self.assertIn("# V-IPM Baseline Design Report", text)
        self.assertIn("MockJmagAdapter.fixed_fixture", text)
        self.assertIn("JMAG live verification status", text)
        self.assertIn("not verified", text.lower())


if __name__ == "__main__":
    unittest.main()
