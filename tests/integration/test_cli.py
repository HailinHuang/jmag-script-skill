import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_promotion_cannot_bypass_approval_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "candidate.json"
            candidate.write_text(json.dumps({"id": "sample", "state": "verified"}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "jmag_skill.cli", "promote", str(candidate)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(candidate.read_text(encoding="utf-8"))["state"], "verified")


if __name__ == "__main__": unittest.main()
