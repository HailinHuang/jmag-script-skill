"""Smoke tests for standalone scripts in jmag_user_py."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import unittest


ROOT = Path(__file__).parents[2]
SCRIPT_NAMES = (
    "export_testmodel1_inventory_visual.py",
    "generate_testmodel1_report.py",
    "open_testmodel1_visible_and_run.py",
    "probe_testmodel1.py",
    "render_saved_inventory_visual.py",
    "script_editor_xy_sketch.py",
    "testmodel1_function_test.py",
)


class JmagUserScriptTests(unittest.TestCase):
    def test_scripts_expose_help_without_running_jmag(self):
        for name in SCRIPT_NAMES:
            with self.subTest(script=name):
                completed = subprocess.run(
                    [sys.executable, str(ROOT / "jmag_user_py" / name), "--help"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn("usage:", completed.stdout.lower())
