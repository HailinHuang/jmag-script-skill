from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]


class FrontendFlowBoundaryTests(unittest.TestCase):
    def test_frontend_flow_package_is_not_present(self):
        self.assertFalse((ROOT / "src/jmag_skill/frontend").exists())
        text = (ROOT / "docs/FRONTEND_USAGE.md").read_text(encoding="utf-8").lower()
        self.assertIn("planned", text)
        self.assertIn("not present", text)


if __name__ == "__main__":
    unittest.main()
