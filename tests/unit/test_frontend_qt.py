from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]


class FrontendQtBoundaryTests(unittest.TestCase):
    def test_pyside6_entrypoints_are_planned_not_optional_skips(self):
        self.assertFalse((ROOT / "run_frontend.cmd").exists())
        self.assertFalse((ROOT / "requirements-frontend.txt").exists())
        self.assertFalse((ROOT / "src/jmag_skill/frontend").exists())
        text = (ROOT / "docs/FRONTEND_USAGE.md").read_text(encoding="utf-8").lower()
        self.assertIn("planned", text)


if __name__ == "__main__":
    unittest.main()
