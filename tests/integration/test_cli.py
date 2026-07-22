import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_module_help_lists_only_the_committed_commands(self):
        root = Path(__file__).parents[2]
        environment = dict(os.environ, PYTHONPATH=str(root / "src"))
        result = subprocess.run(
            [sys.executable, "-m", "jmag_skill.cli", "--help"],
            cwd=root,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ("search", "help", "inspect", "promote", "sync", "rollback", "verify", "build-index"):
            self.assertIn(command, result.stdout)
        for command in ("validate-design", "plan-design", "execute-design", "execute-offline", "size-design", "prepare-optimization", "generate-report", "submit-mock-job", "inspect-jmdl"):
            self.assertNotIn(command, result.stdout)

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
