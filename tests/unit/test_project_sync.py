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
                {"id": "session.context", "status": "stable", "module": "session.py", "dependencies": []},
                {"id": "results.get", "status": "stable", "module": "results.py", "dependencies": []},
            ]
            lock = sync_project(project, ["session.context"], catalog, library,
                                library_version="0.1.0", git_commit="abc", jmag_version="25.1")
            self.assertTrue((project / "jmag_functions" / "session.py").exists())
            self.assertTrue((project / "jmag_functions" / "__init__.py").exists())
            self.assertFalse((project / "jmag_functions" / "results.py").exists())
            self.assertTrue((project / ".jmag" / "candidates").is_dir())
            self.assertTrue((project / ".claude" / "memory").is_dir())
            self.assertEqual(lock["functions"][0]["id"], "session.context")
            persisted = json.loads((project / "jmag-functions.lock.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted["jmag_version"], "25.1")

            (library / "session.py").write_text("SESSION = 2\n", encoding="utf-8")
            sync_project(project, ["session.context"], catalog, library,
                         library_version="0.2.0", git_commit="def", jmag_version="25.1")
            self.assertIn("SESSION = 2", (project / "jmag_functions" / "session.py").read_text())
            rollback_project(project)
            self.assertIn("SESSION = 1", (project / "jmag_functions" / "session.py").read_text())


if __name__ == "__main__": unittest.main()
