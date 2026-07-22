from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jmag_skill.frontend.capabilities import CapabilityRegistry
from jmag_skill.frontend.flow import AgentFlowService
from jmag_skill.frontend.session import STAGES, StageStatus


REQUIREMENTS = {
    "design_goal": "traction motor baseline",
    "rated_power_kw": 110.0,
    "rated_speed_rpm": 3000.0,
    "peak_torque_nm": 350.0,
    "maximum_speed_rpm": 6000.0,
    "dc_voltage_v": 800.0,
    "cooling_method": "water",
    "winding_temperature_limit_c": 180.0,
    "magnet_temperature_limit_c": 150.0,
    "demagnetization_margin": 1.15,
    "topology": "SPM",
    "phases": 3,
    "poles": 8,
    "slots": 48,
}


class FrontendFlowTests(unittest.TestCase):
    def test_new_session_starts_at_requirements_with_next_actions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = AgentFlowService(Path(temp_dir))
            session = service.create_session()

            self.assertEqual(session.current_stage, "requirements")
            self.assertEqual(session.stage_states["requirements"], StageStatus.PENDING.value)
            self.assertEqual(session.evidence_status, "mock_only")
            self.assertTrue(service.get_next_actions(session.session_id))

    def test_missing_requirements_block_stage_and_report_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = AgentFlowService(Path(temp_dir))
            session = service.create_session()

            event = service.continue_stage(session.session_id)

            self.assertEqual(event["status"], "blocked")
            self.assertIn("rated_power_kw", event["missing_fields"])
            self.assertEqual(event["stage"], "requirements")

    def test_confirmed_context_unlocks_next_stage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = AgentFlowService(Path(temp_dir))
            session = service.create_session()
            service.handle_intent(session.session_id, "update_context", REQUIREMENTS)

            event = service.continue_stage(session.session_id)
            refreshed = service.get_session(session.session_id)

            self.assertEqual(event["status"], "completed")
            self.assertEqual(event["next_stage"], "operating_points")
            self.assertEqual(refreshed.stage_states["requirements"], StageStatus.COMPLETED.value)
            self.assertEqual(refreshed.current_stage, "operating_points")

    def test_context_change_marks_downstream_results_stale(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = AgentFlowService(Path(temp_dir))
            session = service.create_session()
            service.handle_intent(session.session_id, "update_context", REQUIREMENTS)
            for _ in range(4):
                service.continue_stage(session.session_id)
            self.assertEqual(service.get_session(session.session_id).current_stage, "material_screening")

            service.handle_intent(session.session_id, "update_context", {"rated_power_kw": 125.0})
            refreshed = service.get_session(session.session_id)

            self.assertEqual(refreshed.stage_states["requirements"], StageStatus.STALE.value)
            self.assertEqual(refreshed.stage_states["preliminary_sizing"], StageStatus.STALE.value)
            self.assertEqual(refreshed.stage_states["material_screening"], StageStatus.STALE.value)

    def test_capability_registry_exposes_mock_ledger(self):
        registry = CapabilityRegistry.default()
        records = registry.records()

        self.assertIn("mock_geometry_builder", records)
        self.assertIn("create_geometry_editor", records["mock_geometry_builder"]["intended_jmag_functions"])
        self.assertEqual(records["mock_geometry_builder"]["evidence_status"], "synthetic_mock")
        self.assertIn("mock_result_extractor", records)

    def test_abstract_topology_completes_mock_flow_and_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = AgentFlowService(Path(temp_dir))
            session = service.create_session()
            service.handle_intent(session.session_id, "update_context", REQUIREMENTS)

            events = [service.continue_stage(session.session_id) for _ in STAGES]
            refreshed = service.get_session(session.session_id)
            session_dir = Path(temp_dir) / session.session_id

            self.assertEqual(refreshed.status, "completed")
            self.assertEqual(refreshed.current_stage, "completed")
            self.assertEqual(events[-1]["stage"], "candidate_report")
            self.assertTrue((session_dir / "session.json").is_file())
            self.assertTrue((session_dir / "stages" / "geometry_mock.json").is_file())
            self.assertTrue((session_dir / "stages" / "results_mock.json").is_file())
            self.assertTrue((session_dir / "results" / "result_bundle.json").is_file())
            self.assertTrue((session_dir / "candidates" / "candidate_summary.json").is_file())
            self.assertTrue((session_dir / "report" / "design_report.md").is_file())
            result = json.loads((session_dir / "stages" / "results_mock.json").read_text(encoding="utf-8"))
            self.assertEqual(result["evidence_status"], "synthetic_mock")

    def test_retry_stage_reexecutes_current_stage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = AgentFlowService(Path(temp_dir))
            session = service.create_session()
            service.handle_intent(session.session_id, "update_context", REQUIREMENTS)
            service.continue_stage(session.session_id)
            before = len(service.get_session(session.session_id).events)

            event = service.retry_stage(session.session_id)

            self.assertEqual(event["status"], "completed")
            self.assertGreater(len(service.get_session(session.session_id).events), before)

    def test_v_ipm_uses_detailed_mock_geometry_and_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = AgentFlowService(Path(temp_dir))
            session = service.create_session()
            requirements = dict(REQUIREMENTS)
            requirements["topology"] = "V-IPM"
            service.handle_intent(session.session_id, "update_context", requirements)

            for _ in STAGES:
                service.continue_stage(session.session_id)

            refreshed = service.get_session(session.session_id)
            geometry = refreshed.stage_outputs["geometry_mock"]
            results = refreshed.stage_outputs["results_mock"]

            self.assertEqual(geometry["capability"], "v_ipm_detailed_geometry")
            self.assertEqual(geometry["evidence_status"], "mock_only")
            self.assertEqual(results["evidence_status"], "mock_only")
            self.assertEqual(results["metrics"]["average_torque"]["value"], 350.0)


if __name__ == "__main__":
    unittest.main()
