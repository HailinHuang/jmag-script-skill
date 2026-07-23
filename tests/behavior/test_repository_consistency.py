from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path

from jmag_functions import __all__ as public_exports
from jmag_skill.cli import build_parser


ROOT = Path(__file__).parents[2]
COMMANDS = {"search", "help", "inspect", "promote", "sync", "rollback", "verify", "build-index"}
PLANNED_PATHS = (
    "src/jmag_skill/executor",
    "src/jmag_skill/offline",
    "src/jmag_skill/frontend",
    "examples",
)
EXPECTED_CATALOG_IDS = {
    "session.context",
    "results.get_value",
    "results.get_values",
    "design_table.set_parameter",
    "design_table.set_parameters",
    "study.run_cases",
}


class RepositoryConsistencyTests(unittest.TestCase):
    def test_cli_command_set_is_exact(self):
        parser = build_parser()
        action = next(item for item in parser._actions if item.dest == "command")
        self.assertEqual(set(action.choices), COMMANDS)

    def test_missing_paths_and_docs_are_explicitly_planned(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        build_plan = (ROOT / "docs/JMAG_CAPABILITY_BUILD_PLAN.md").read_text(encoding="utf-8").lower()
        frontend = (ROOT / "docs/FRONTEND_USAGE.md").read_text(encoding="utf-8").lower()
        for path in PLANNED_PATHS:
            self.assertFalse((ROOT / path).exists(), path)
        for term in ("designspec executor", "offline workflow", "pyside6 design frontend", "v-ipm reference workflow", "inspect-jmdl"):
            self.assertIn("planned", readme)
            self.assertIn(term, readme)
        self.assertIn("planned", build_plan)
        self.assertIn("not present", build_plan)
        self.assertIn("planned", frontend)

    def test_runtime_frontend_path_exists(self):
        self.assertTrue((ROOT / "jmag_user_py/jmag_runtime_frontend.py").is_file())

    def test_catalog_is_the_original_verified_set_without_stable_entries(self):
        catalog = json.loads((ROOT / "references/function-catalog.json").read_text(encoding="utf-8"))
        self.assertEqual({item["id"] for item in catalog["functions"]}, EXPECTED_CATALOG_IDS)
        self.assertEqual({item["status"] for item in catalog["functions"]}, {"verified"})
        self.assertNotIn("stable", {item["status"] for item in catalog["functions"]})
        for entry in catalog["functions"]:
            module = importlib.import_module(f"jmag_functions.{Path(entry['module']).stem}")
            self.assertTrue(hasattr(module, entry["symbol"]))

    def test_public_exports_are_separate_from_capability_status(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertGreater(len(public_exports), 6)
        self.assertIn("public export is not automatically", readme)

    def test_package_discovery_and_entry_point_are_preserved(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('package-dir = {"" = "src"}', pyproject)
        self.assertIn('where = ["src"]', pyproject)
        self.assertIn('jmag-skill = "jmag_skill.cli:main"', pyproject)

    def test_maintained_docs_and_ignore_rules_match_repository_truth(self):
        docs = [ROOT / "README.md", ROOT / "SKILL.md", ROOT / "docs/current_status.md"]
        for document in docs:
            text = document.read_text(encoding="utf-8")
            self.assertIn("JMAG Designer 25.1", text)
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in ("*.jproj", "*.jfiles/", "*.jplot", "*.jmdl", "artifacts/", "tmp/"):
            self.assertIn(pattern, ignored)

    def test_m1_protected_copy_contract_is_public_and_scoped(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        lifecycle = (ROOT / "src/jmag_functions/PROJECT_LIFECYCLE.md").read_text(encoding="utf-8")
        smoke = ROOT / "jmag_user_py/smoke/m1_existing_project_lifecycle_smoke.py"
        for export in (
            "ProjectBundle",
            "ManagedProjectSession",
            "copy_project_bundle",
            "open_protected_project_copy",
            "load_protected_project_copy",
        ):
            self.assertIn(export, public_exports)
        self.assertIn("filesystem-level", readme)
        self.assertIn("Geometry, change parameters, or execute cases", readme)
        self.assertIn("Never modify the source directly", skill)
        self.assertIn("legacy convenience", lifecycle)
        self.assertTrue(smoke.is_file())


if __name__ == "__main__":
    unittest.main()
