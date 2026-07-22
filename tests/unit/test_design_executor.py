from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from jmag_skill.executor.adapters.mock_jmag import MockJmagAdapter
from jmag_skill.executor.spec_loader import load_design_spec
from jmag_skill.executor.spec_resolver import SpecValidationError, resolve_design_spec
from jmag_skill.executor.workflow import execute_design
from jmag_skill.cli import main


ROOT = Path(__file__).parents[2]
SPEC = ROOT / "examples" / "design_specs" / "design_spec.yaml"


class DesignExecutorTests(unittest.TestCase):
    def test_validate_cli_accepts_the_example_spec(self):
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["validate-design", str(SPEC)])

        self.assertEqual(exit_code, 0)
        self.assertIn('"status": "valid"', output.getvalue())

    def test_execute_cli_mock_accepts_an_explicit_run_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_directory = Path(temp_dir) / "cli-run"
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "execute-design",
                        str(SPEC),
                        "--adapter",
                        "mock",
                        "--run-directory",
                        str(run_directory),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue((run_directory / "result_bundle.json").is_file())

    def test_loads_explicit_v_ipm_yaml_without_external_runtime_state(self):
        spec = load_design_spec(SPEC)

        self.assertEqual(spec["machine"]["topology"], "v_ipm")
        self.assertEqual(spec["machine"]["dimension"], "2d")
        self.assertEqual(spec["execution"]["overwrite_existing_target"], False)

    def test_resolver_rejects_unsupported_topology_before_execution(self):
        spec = load_design_spec(SPEC)
        spec["machine"]["topology"] = "spm"

        with self.assertRaises(SpecValidationError):
            resolve_design_spec(spec)

    def test_mock_execution_writes_reproducible_run_artifacts(self):
        spec = resolve_design_spec(load_design_spec(SPEC))

        with tempfile.TemporaryDirectory() as temp_dir:
            run_directory = Path(temp_dir) / "run"
            result = execute_design(
                spec,
                MockJmagAdapter(),
                run_directory,
                input_spec_path=SPEC,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["machine"]["topology"], "v_ipm")
            self.assertIn("average_torque", result["metrics"])
            self.assertIn("efficiency", result["derived_metrics"])
            self.assertEqual(result["validation"]["status"], "passed")

            manifest = json.loads(
                (run_directory / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(
                manifest["completed_stages"],
                [
                    "validated",
                    "resolved",
                    "planned",
                    "geometry",
                    "study",
                    "solve",
                    "extract",
                ],
            )
            for relative_path in (
                "input_spec.yaml",
                "resolved_spec.json",
                "execution_plan.json",
                "events.jsonl",
                "capability_record.json",
                "result_bundle.json",
                "project/v_ipm_baseline.mock.jproj",
            ):
                self.assertTrue((run_directory / relative_path).is_file())


if __name__ == "__main__":
    unittest.main()
