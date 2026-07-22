import json
import re
import unittest
from pathlib import Path

from jmag_skill.cli import build_parser


ROOT = Path(__file__).parents[2]


class RepositoryConsistencyTests(unittest.TestCase):
    def test_checkpoint_documents_exist_and_describe_current_boundaries(self):
        current_status = (ROOT / "docs/current_status.md").read_text(encoding="utf-8")
        implementation_plan = (ROOT / "docs/implementation_plan.md").read_text(
            encoding="utf-8"
        )

        for text in (current_status, implementation_plan):
            self.assertIn("offline executor", text.lower())
            self.assertIn("mock-only", text.lower())
            self.assertIn("inspect-jmdl", text)
            self.assertIn("geometry live vertical slice", text.lower())

    def test_readme_uses_catalog_as_status_authority_without_fixed_count(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        catalog = json.loads(
            (ROOT / "references/function-catalog.json").read_text(encoding="utf-8")
        )

        self.assertIn("references/function-catalog.json", readme)
        self.assertNotRegex(readme, r"contains (?:eleven|\d+) `verified`")
        self.assertIn("inspect-jmdl", readme)
        self.assertIn("not implemented", readme.lower())
        self.assertEqual({item["status"] for item in catalog["functions"]}, {"verified"})

    def test_lifecycle_document_matches_catalog_lifecycle(self):
        lifecycle = (ROOT / "docs/JMAG_PROJECT_LIFECYCLE.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("references/function-catalog.json", lifecycle)
        self.assertIn("verified", lifecycle)
        self.assertIn("stable", lifecycle)
        self.assertNotIn("functions remain observed candidates", lifecycle.lower())

    def test_cli_and_mock_boundaries_are_explicit(self):
        help_text = build_parser().format_help()
        mock_adapter_help = build_parser().parse_args(
            ["execute-design", "examples/design_specs/design_spec.yaml"]
        )

        self.assertIn("execute-design", help_text)
        self.assertNotIn("inspect-jmdl", help_text)
        self.assertEqual(mock_adapter_help.adapter, "mock")
        self.assertIn(
            "mock_only",
            (ROOT / "src/jmag_skill/executor/adapters/mock_jmag.py")
            .read_text(encoding="utf-8")
            .lower(),
        )


if __name__ == "__main__":
    unittest.main()
