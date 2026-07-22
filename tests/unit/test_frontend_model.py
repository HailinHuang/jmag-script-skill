from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jmag_skill.frontend.model import ChatMessage, classify_command, metric_rows
from jmag_skill.frontend.runner import OfflineFrontendService


ROOT = Path(__file__).parents[2]
SPEC = ROOT / "examples" / "design_specs" / "design_spec.yaml"


class FrontendModelTests(unittest.TestCase):
    def test_classifies_common_commands(self):
        self.assertEqual(classify_command("执行离线基线"), "run_offline")
        self.assertEqual(classify_command("run mock"), "run_offline")
        self.assertEqual(classify_command("开始初步设计"), "start_design")
        self.assertEqual(classify_command("确认并继续"), "continue_stage")
        self.assertEqual(classify_command("查看当前 Agent 能力"), "view_capabilities")
        self.assertEqual(classify_command("help"), "help")
        self.assertEqual(classify_command("随便聊聊"), "unknown")

    def test_chat_message_keeps_role_and_text(self):
        message = ChatMessage("assistant", "ready")

        self.assertEqual(message.role, "assistant")
        self.assertEqual(message.text, "ready")

    def test_metric_rows_flattens_metrics_and_derived_metrics(self):
        rows = metric_rows(
            {
                "metrics": {
                    "average_torque": {"status": "available", "value": 12.5, "unit": "N*m"}
                },
                "derived_metrics": {
                    "efficiency": {"status": "available", "value": 0.95, "unit": "1"}
                },
            }
        )

        self.assertEqual(rows[0][0], "average_torque")
        self.assertEqual(rows[1][0], "efficiency")
        self.assertEqual(rows[1][3], "derived")

    def test_offline_frontend_service_runs_without_jmag(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = OfflineFrontendService().run(SPEC, Path(temp_dir) / "frontend-run", maximum_cases=9)

            self.assertEqual(result["status"], "completed")
            self.assertTrue((Path(temp_dir) / "frontend-run" / "report" / "design_report.md").is_file())
            self.assertEqual(result["evidence_status"], "offline_and_mock_only")


if __name__ == "__main__":
    unittest.main()
