from __future__ import annotations

import unittest
from pathlib import Path

from jmag_skill.cli import build_parser


ROOT = Path(__file__).parents[2]


class DesignExecutorBoundaryTests(unittest.TestCase):
    def test_executor_is_planned_and_has_no_package_or_command(self):
        self.assertFalse((ROOT / "src/jmag_skill/executor").exists())
        self.assertNotIn("execute-design", build_parser().format_help())
        text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("designspec executor", text)
        self.assertIn("planned", text)


if __name__ == "__main__":
    unittest.main()
