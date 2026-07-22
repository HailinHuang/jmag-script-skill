from __future__ import annotations

import unittest
from pathlib import Path

from jmag_skill.cli import build_parser


ROOT = Path(__file__).parents[2]


class OfflineCapabilityBoundaryTests(unittest.TestCase):
    def test_offline_workflow_is_planned_and_has_no_package_or_command(self):
        self.assertFalse((ROOT / "src/jmag_skill/offline").exists())
        self.assertNotIn("execute-offline", build_parser().format_help())
        text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("offline workflow", text)
        self.assertIn("planned", text)


if __name__ == "__main__":
    unittest.main()
