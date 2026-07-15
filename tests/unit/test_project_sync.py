import json
import tempfile
import unittest
from pathlib import Path

from jmag_skill.project_sync import rollback_project, sync_project


class SyncTests(unittest.TestCase):
    def test_sync_copies_only_requested_functions_and_writes_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "library"
            project = root / "project"
            library.mkdir()
            (library / "session.py").write_text("SESSION = 1\n", encoding="utf-8")
            (library / "results.py").write_text("RESULTS = 1\n", encoding="utf-8")
            catalog = [
                {"id": "session.context", "status": "stable", "module": "session.py", "symbol": "JMAGContext", "dependencies": []},
                {"id": "results.get", "status": "stable", "module": "results.py", "symbol": "get_value", "dependencies": []},
            ]
            lock = sync_project(project, ["session.context"], catalog, library,
                                library_version="0.1.0", git_commit="abc", jmag_version="25.1")
            self.assertTrue((project / "jmag_functions" / "session.py").exists())
            self.assertTrue((project / "jmag_functions" / "__init__.py").exists())
            self.assertIn("JMAGContext", (project / "jmag_functions" / "__init__.py").read_text())
            self.assertFalse((project / "jmag_functions" / "results.py").exists())
            self.assertTrue((project / ".jmag" / "candidates").is_dir())
            self.assertTrue((project / ".claude" / "memory").is_dir())
            self.assertEqual(lock["functions"][0]["id"], "session.context")
            persisted = json.loads((project / "jmag-functions.lock.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted["jmag_version"], "25.1")
            self.assertTrue(list((project / ".claude" / "memory").rglob("jmag-sync-*.md")))

            (library / "session.py").write_text("SESSION = 2\n", encoding="utf-8")
            sync_project(project, ["session.context"], catalog, library,
                         library_version="0.2.0", git_commit="def", jmag_version="25.1")
            self.assertIn("SESSION = 2", (project / "jmag_functions" / "session.py").read_text())
            rollback_project(project)
            self.assertIn("SESSION = 1", (project / "jmag_functions" / "session.py").read_text())

    def test_sync_rejects_path_traversal_and_removes_stale_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); library = root / "library"; project = root / "project"
            library.mkdir()
            (library / "a.py").write_text("def a(): return 1\n", encoding="utf-8")
            (library / "b.py").write_text("def b(): return 2\n", encoding="utf-8")
            catalog = [
                {"id": "a", "status": "stable", "module": "a.py", "symbol": "a", "dependencies": []},
                {"id": "b", "status": "stable", "module": "b.py", "symbol": "b", "dependencies": []},
            ]
            sync_project(project, ["a", "b"], catalog, library, library_version="1", git_commit="a", jmag_version="25.1")
            sync_project(project, ["a"], catalog, library, library_version="2", git_commit="b", jmag_version="25.1")
            self.assertFalse((project / "jmag_functions" / "b.py").exists())
            bad = [{"id": "bad", "status": "stable", "module": "../escape.py", "symbol": "bad", "dependencies": []}]
            with self.assertRaises(ValueError):
                sync_project(project, ["bad"], bad, library, library_version="3", git_commit="c", jmag_version="25.1")
            self.assertFalse((project / "escape.py").exists())


if __name__ == "__main__": unittest.main()
