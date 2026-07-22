"""Offline help checks for repository-local JMAG scripts."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).parents[2]
SAFE_HELP_SCRIPTS = (
    "generate_testmodel1_report.py",
    "open_testmodel1_visible_and_run.py",
    "render_saved_inventory_visual.py",
    "script_editor_xy_sketch.py",
    "testmodel1_function_test.py",
)
JMAG_RUNTIME_SCRIPTS = (
    "export_testmodel1_inventory_visual.py",
    "probe_testmodel1.py",
)


class JmagUserScriptTests(unittest.TestCase):
    def test_safe_scripts_expose_help_with_system_python(self):
        environment = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        for name in SAFE_HELP_SCRIPTS:
            with self.subTest(script=name):
                completed = subprocess.run(
                    [sys.executable, str(ROOT / "jmag_user_py" / name), "--help"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    env=environment,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn("usage:", completed.stdout.lower())

    def test_jmag_bound_scripts_are_not_claimed_as_system_python_help(self):
        for name in JMAG_RUNTIME_SCRIPTS:
            text = (ROOT / "jmag_user_py" / name).read_text(encoding="utf-8")
            self.assertIn("from jmag.designer", text)


if __name__ == "__main__":
    unittest.main()
