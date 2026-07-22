from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest

from jmag_functions.runtime import OperationResult, RuntimeSnapshot, RuntimeTarget
from jmag_user_py.jmag_runtime_frontend import (
    RuntimeFrontendApp,
    RuntimeFrontendModel,
    format_runtime_target,
    operation_result_messages,
)


class FakeManager:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.refresh_count = 0
        self.action_calls = []

    def refresh(self):
        self.refresh_count += 1
        return self.snapshot

    def bring_to_front(self, target_id):
        self.action_calls.append(("bring_to_front", target_id))
        return OperationResult(target_id, "bring_to_front", True, "window state changed")

    def minimize_to_background(self, target_id):
        self.action_calls.append(("minimize_to_background", target_id))
        return OperationResult(target_id, "minimize_to_background", True, "window state changed")

    def stop_selected_jobs(self, target_ids):
        self.action_calls.append(("stop_selected_jobs", tuple(target_ids)))
        return [OperationResult(target_ids[0], "stop", True, "job cancelled")]

    def close_selected_designers(self, target_ids, save=False):
        self.action_calls.append(("close_selected_designers", tuple(target_ids), save))
        return [OperationResult(target_ids[0], "close", True, "Designer closed")]

    def terminate_selected_processes(self, target_ids, force=False):
        self.action_calls.append(("terminate_selected_processes", tuple(target_ids), force))
        return [OperationResult(target_ids[0], "terminate", True, "process terminated")]


class FakeRoot:
    def __init__(self):
        self.after_calls = []
        self.protocol_calls = []
        self.destroyed = False

    def after(self, delay, callback):
        self.after_calls.append((delay, callback))
        return "timer-1"

    def after_cancel(self, timer):
        self.after_calls.append(("cancel", timer))

    def protocol(self, name, callback):
        self.protocol_calls.append((name, callback))

    def destroy(self):
        self.destroyed = True


class FakeTree:
    def __init__(self, selected=()):
        self.selected = tuple(selected)
        self.rows = {}
        self.deleted = []

    def selection(self):
        return self.selected

    def get_children(self):
        return tuple(self.rows)

    def delete(self, item):
        self.deleted.append(item)
        self.rows.pop(item, None)

    def insert(self, _parent, _index, iid, values):
        self.rows[iid] = tuple(values)

    def selection_set(self, item):
        self.selected = (item,)


class FakeText:
    def __init__(self):
        self.lines = []

    def configure(self, **_kwargs):
        return None

    def insert(self, _index, text):
        self.lines.append(text)

    def see(self, _index):
        return None


class RuntimeFrontendModelTests(unittest.TestCase):
    def test_format_runtime_target_includes_process_and_project_fields(self):
        target = RuntimeTarget(
            target_id="process:321",
            kind="process",
            pid=321,
            project_path=Path(r"C:\Models\motor.jproj"),
            status="running",
            window_handle=777,
            attached=False,
            metadata={"process_name": "designer.exe"},
        )
        self.assertEqual(
            format_runtime_target(target),
            ("process", "process:321", "321", "running", "", r"C:\Models\motor.jproj", "777", "No"),
        )

    def test_format_runtime_target_renders_progress_and_missing_values(self):
        target = RuntimeTarget("scheduler:x", "scheduler", status="running", progress=62.5)
        self.assertEqual(
            format_runtime_target(target),
            ("scheduler", "scheduler:x", "", "running", "62.5%", "", "", "No"),
        )

    def test_model_refresh_delegates_to_manager(self):
        snapshot = RuntimeSnapshot(diagnostics=("process discovery: denied",))
        manager = FakeManager(snapshot)
        model = RuntimeFrontendModel(manager)
        self.assertIs(model.refresh(), snapshot)
        self.assertEqual(manager.refresh_count, 1)

    def test_operation_result_messages_include_target_and_error(self):
        results = [
            OperationResult("designer:99", "close", True, "Designer closed"),
            OperationResult(
                "process:321",
                "terminate",
                False,
                "process termination failed",
                "OSError: denied",
            ),
        ]
        self.assertEqual(
            operation_result_messages(results),
            [
                "[OK] designer:99: Designer closed",
                "[ERROR] process:321: process termination failed (OSError: denied)",
            ],
        )


class RuntimeFrontendAppTests(unittest.TestCase):
    def _make_app(self, *, selected=("process:321",)):
        target = RuntimeTarget("process:321", "process", pid=321, status="running")
        manager = FakeManager(RuntimeSnapshot(targets=(target,)))
        app = RuntimeFrontendApp.__new__(RuntimeFrontendApp)
        app.root = FakeRoot()
        app.manager = manager
        app.model = RuntimeFrontendModel(manager)
        app.tree = FakeTree(selected)
        app.log = FakeText()
        app._timer = None
        app._closed = False
        app.poll_ms = 2000
        app.current_snapshot = manager.snapshot
        return app, manager

    def test_refresh_keeps_existing_selection_when_target_remains(self):
        app, manager = self._make_app()
        app.refresh(schedule=False)
        self.assertEqual(app.tree.selection(), ("process:321",))
        self.assertEqual(manager.refresh_count, 1)
        self.assertIn("process:321", app.tree.rows)

    def test_action_handlers_call_manager_for_selected_target(self):
        app, manager = self._make_app()
        app.bring_selected_to_front()
        app.minimize_selected()
        app.stop_selected()
        self.assertEqual(
            [call[0] for call in manager.action_calls],
            ["bring_to_front", "minimize_to_background", "stop_selected_jobs"],
        )

    def test_force_terminate_passes_force_true_only_after_confirmation(self):
        app, manager = self._make_app()
        app.confirm_force_termination = lambda _target: True
        app.force_terminate_selected()
        self.assertEqual(
            manager.action_calls[-1],
            ("terminate_selected_processes", ("process:321",), True),
        )

    def test_force_terminate_does_not_call_manager_when_cancelled(self):
        app, manager = self._make_app()
        app.confirm_force_termination = lambda _target: False
        app.force_terminate_selected()
        self.assertEqual(manager.action_calls, [])

    def test_close_cancels_timer_and_destroys_root(self):
        app, _manager = self._make_app()
        app._timer = "timer-1"
        app.close()
        self.assertIn(("cancel", "timer-1"), app.root.after_calls)
        self.assertTrue(app.root.destroyed)


class RuntimeFrontendEntrypointTests(unittest.TestCase):
    def test_help_does_not_start_tk_or_jmag(self):
        root = Path(__file__).parents[2]
        env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        completed = subprocess.run(
            [sys.executable, str(root / "jmag_user_py" / "jmag_runtime_frontend.py"), "--help"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
            env={**env, "PYTHONPATH": str(root / "src")},
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("usage:", completed.stdout.lower())
        self.assertIn("JMAG Runtime Frontend", completed.stdout)


if __name__ == "__main__":
    unittest.main()
