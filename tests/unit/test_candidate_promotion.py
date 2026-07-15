import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from jmag_skill.candidate import inspect_function
from jmag_skill.promotion import PromotionError, promote


class CandidatePromotionTests(unittest.TestCase):
    def test_inspect_finds_globals_paths_and_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text('ROOT = "D:/project"\ndef useful(app, case=1):\n    return app.GetStudy("Main").Run()\n', encoding="utf-8")
            manifest = inspect_function(path, "useful")
            self.assertEqual(manifest["state"], "observed")
            self.assertIn("ROOT", manifest["global_dependencies"])
            self.assertIn("D:/project", manifest["hardcoded_paths"])
            self.assertIn("GetStudy", manifest["jmag_methods"])
            self.assertEqual(manifest["source_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_promotion_requires_verified_and_explicit_approval(self):
        manifest = {"id": "x", "state": "candidate"}
        with self.assertRaises(PromotionError): promote(manifest, approved=True)
        manifest["state"] = "verified"
        with self.assertRaises(PromotionError): promote(manifest, approved=False)
        result = promote(manifest, approved=True)
        self.assertEqual(result["state"], "approved")


if __name__ == "__main__": unittest.main()
