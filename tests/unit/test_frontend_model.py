from __future__ import annotations

import unittest
from pathlib import Path

from jmag_skill.cli import build_parser


ROOT = Path(__file__).parents[2]


class FrontendModelBoundaryTests(unittest.TestCase):
    def test_design_frontend_commands_are_not_available(self):
        help_text = build_parser().format_help()
        self.assertNotIn("run_frontend", help_text)
        self.assertNotIn("execute-design", help_text)
        text = (ROOT / "docs/FRONTEND_USAGE.md").read_text(encoding="utf-8").lower()
        self.assertIn("pyside6 design frontend", text)
        self.assertIn("planned", text)


if __name__ == "__main__":
    unittest.main()
