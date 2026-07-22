from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    from jmag_skill.frontend.app import MainWindow
except (ImportError, RuntimeError):
    QApplication = None
    MainWindow = None


@unittest.skipUnless(QApplication is not None, "PySide6 is available in the project .venv only")
class FrontendQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_window_exposes_chat_and_result_views(self):
        window = MainWindow()

        self.assertIn("JMAG Design", window.windowTitle())
        self.assertEqual(window.result_tabs.count(), 7)
        self.assertIsNotNone(window.stage_list)
        self.assertIsNotNone(window.capability_view)
        self.assertIsNotNone(window.next_actions_view)
        self.assertTrue(window.command_input.isEnabled())
        window.close()

    def test_apply_flow_event_updates_current_capability_and_actions(self):
        window = MainWindow()
        window.apply_flow_event(
            {
                "kind": "stage_completed",
                "stage": "requirements",
                "status": "completed",
                "summary": "需求已确认。",
                "current_stage": "operating_points",
                "stage_snapshot": {"label": "需求收集", "status": "completed", "summary": "需求已确认。"},
                "next_actions": [{"action_id": "continue_stage", "label": "确认并进入工况与约束"}],
            }
        )

        self.assertIn("operating_points", window.current_stage_value.text())
        self.assertIn("需求已确认", window.capability_view.toPlainText())
        self.assertIn("确认并进入工况与约束", window.next_actions_view.toPlainText())
        window.close()

    def test_apply_result_updates_metric_and_report_views(self):
        window = MainWindow()
        window.apply_result(
            {
                "status": "completed",
                "run_directory": "run-001",
                "result_bundle": {
                    "metrics": {
                        "average_torque": {"status": "available", "value": 350.0, "unit": "N*m"}
                    },
                    "derived_metrics": {
                        "efficiency": {"status": "available", "value": 0.96, "unit": "1"}
                    },
                    "validation": {"status": "passed"},
                },
                "report_text": "# Baseline report\n\nCompleted.",
            }
        )

        self.assertEqual(window.status_value.text(), "completed")
        self.assertEqual(window.metrics_table.rowCount(), 2)
        self.assertIn("Baseline report", window.report_view.toPlainText())
        window.close()


if __name__ == "__main__":
    unittest.main()
