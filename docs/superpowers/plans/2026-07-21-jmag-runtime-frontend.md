# JMAG Runtime Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dependency-free Tkinter frontend at the repository root for inspecting and safely controlling JMAG runtime targets through `JMAGRuntimeManager`.

**Architecture:** Keep `src/jmag_functions/runtime.py` as the source of truth for JMAG and Windows actions. Add a thin root-level `jmag_runtime_frontend.py` containing a testable presentation model, Tkinter widgets, polling, and a safe executable entrypoint. Inject the manager and Tk root in tests so no JMAG process or real window is needed for unit verification.

**Tech Stack:** Python 3.10+, standard-library `tkinter`/`ttk`, `argparse`, existing `unittest`, and `jmag_functions.runtime`.

## Global Constraints

- Inspection is read-only and must never call `Save`, `Cancel`, `Quit`, or process termination.
- Normal cancellation must use the existing `JMAGRuntimeManager` APIs.
- Process termination must require explicit authorization and a confirmation dialog.
- Do not add runtime dependencies to `pyproject.toml`.
- Preserve all existing uncommitted user files; modify only the new frontend, its tests, and the frontend documentation entry.
- The executable must parse `--help` before creating a Tk root or touching JMAG.
- The root frontend must add the repository `src` directory to `sys.path` when run directly from the repository.

---

### Task 1: Add pure frontend formatting and operation-model contracts

**Files:**
- Create: `jmag_runtime_frontend.py`
- Create: `tests/unit/test_runtime_frontend.py`

**Interfaces:**
- Consume: `RuntimeSnapshot`, `RuntimeTarget`, and `OperationResult` from `jmag_functions.runtime`.
- Produce: `format_runtime_target(target) -> tuple[str, ...]`, `operation_result_messages(results) -> list[str]`, and `RuntimeFrontendModel.refresh() -> RuntimeSnapshot`.

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path
import unittest

from jmag_functions.runtime import OperationResult, RuntimeSnapshot, RuntimeTarget
from jmag_runtime_frontend import (
    RuntimeFrontendModel,
    format_runtime_target,
    operation_result_messages,
)


class FakeManager:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.refresh_count = 0

    def refresh(self):
        self.refresh_count += 1
        return self.snapshot


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
            OperationResult("process:321", "terminate", False, "process termination failed", "OSError: denied"),
        ]
        self.assertEqual(
            operation_result_messages(results),
            [
                "[OK] designer:99: Designer closed",
                "[ERROR] process:321: process termination failed (OSError: denied)",
            ],
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest tests.unit.test_runtime_frontend -v
```

Expected: collection fails because `jmag_runtime_frontend` does not yet
provide the requested formatting functions and model.

- [ ] **Step 3: Write the minimal implementation**

Add the repository-root `src` path before importing `jmag_functions`, then
implement the pure functions and model exactly as follows:

```python
def _display(value):
    return "" if value is None else str(value)


def format_runtime_target(target):
    progress = "" if target.progress is None else f"{target.progress:.1f}%"
    return (
        target.kind,
        target.target_id,
        _display(target.pid),
        target.status,
        progress,
        _display(target.project_path),
        _display(target.window_handle),
        "Yes" if target.attached else "No",
    )


def operation_result_messages(results):
    messages = []
    for result in results:
        prefix = "OK" if result.ok else "ERROR"
        detail = f" ({result.error})" if result.error else ""
        messages.append(f"[{prefix}] {result.target_id}: {result.message}{detail}")
    return messages


class RuntimeFrontendModel:
    def __init__(self, manager):
        self.manager = manager

    def refresh(self):
        return self.manager.refresh()
```

- [ ] **Step 4: Run the focused test to verify it passes**

Run the same unittest command. Expected: 4 tests pass with zero failures.

---

### Task 2: Add the Tkinter application and safe action handlers

**Files:**
- Modify: `jmag_runtime_frontend.py`
- Modify: `tests/unit/test_runtime_frontend.py`

**Interfaces:**
- Consume: `RuntimeFrontendModel`, `format_runtime_target`, and the existing manager methods.
- Produce: `RuntimeFrontendApp(root, manager=None, poll_ms=2000, start_polling=True)`, `refresh()`, and button handlers for window, JMAG, and process operations.

- [ ] **Step 1: Write the failing tests**

Append tests using a fake Tk root, fake tree, and fake manager:

```python
class FakeRoot:
    def __init__(self):
        self.after_calls = []
        self.protocol_calls = []

    def after(self, delay, callback):
        self.after_calls.append((delay, callback))
        return "timer-1"

    def after_cancel(self, timer):
        self.after_calls.append(("cancel", timer))

    def protocol(self, name, callback):
        self.protocol_calls.append((name, callback))


class FakeManagerWithActions(FakeManager):
    def __init__(self, snapshot):
        super().__init__(snapshot)
        self.action_calls = []

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


class RuntimeFrontendAppTests(unittest.TestCase):
    def test_refresh_keeps_existing_selection_when_target_remains(self):
        target = RuntimeTarget("process:321", "process", pid=321, status="running")
        manager = FakeManagerWithActions(RuntimeSnapshot(targets=(target,)))
        app = RuntimeFrontendApp(FakeRoot(), manager=manager, start_polling=False)
        app.tree.selection = lambda: ("process:321",)
        app.tree.get_children = lambda: ()
        app.refresh()
        self.assertEqual(app.selected_target_id, "process:321")

    def test_action_handlers_call_manager_for_selected_target(self):
        target = RuntimeTarget("process:321", "process", pid=321, status="running")
        manager = FakeManagerWithActions(RuntimeSnapshot(targets=(target,)))
        app = RuntimeFrontendApp(FakeRoot(), manager=manager, start_polling=False)
        app.selected_target_id = "process:321"
        app.bring_selected_to_front()
        app.minimize_selected()
        app.stop_selected()
        self.assertEqual(
            [call[0] for call in manager.action_calls],
            ["bring_to_front", "minimize_to_background", "stop_selected_jobs"],
        )

    def test_force_terminate_passes_force_true_only_after_confirmation(self):
        target = RuntimeTarget("process:321", "process", pid=321, status="running")
        manager = FakeManagerWithActions(RuntimeSnapshot(targets=(target,)))
        app = RuntimeFrontendApp(FakeRoot(), manager=manager, start_polling=False)
        app.selected_target_id = "process:321"
        app.confirm_force_termination = lambda _target: True
        app.force_terminate_selected()
        self.assertEqual(
            manager.action_calls[-1],
            ("terminate_selected_processes", ("process:321",), True),
        )
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest tests.unit.test_runtime_frontend.RuntimeFrontendAppTests -v
```

Expected: the tests fail because `RuntimeFrontendApp` and its handlers do not
yet exist.

- [ ] **Step 3: Write the minimal implementation**

Implement a `ttk.Treeview` with columns `kind`, `id`, `pid`, `status`,
`progress`, `project`, `window`, and `attached`. Build the toolbar, action
buttons, status label, and read-only `tk.Text` log. Implement these methods:

```python
refresh()
selected_target_id()
_run_single_result(operation_name)
bring_selected_to_front()
minimize_selected()
stop_selected()
save_close_selected()
close_selected()
confirm_force_termination(target)
force_terminate_selected()
close()
```

`refresh()` must capture the old selection, call the model, replace rows with
`format_runtime_target`, restore the selection only if its target ID remains,
log snapshot diagnostics, and schedule the next poll with `root.after`. Each
action must report “No target selected” when appropriate, call only the
corresponding manager method, and append `operation_result_messages` to the
log. `confirm_force_termination` must call `tkinter.messagebox.askyesno` with
the selected PID and executable information; `force_terminate_selected` must
return without calling the manager when confirmation is false. `close()` must
cancel the scheduled timer and destroy the root.

- [ ] **Step 4: Run the focused test to verify it passes**

Run the same unittest command. Expected: all frontend model and application
tests pass with zero failures.

---

### Task 3: Add executable entrypoint, help behavior, and usage documentation

**Files:**
- Modify: `jmag_runtime_frontend.py`
- Modify: `tests/unit/test_runtime_frontend.py`
- Modify: `README.md`

**Interfaces:**
- Produce: `build_parser()`, `main(argv=None) -> int`, and a direct script entrypoint.

- [ ] **Step 1: Write the failing test**

Add a subprocess test that runs the script with `--help` without a JMAG
runtime path:

```python
import os
import subprocess
import sys


def test_help_does_not_start_tk_or_jmag():
    root = Path(__file__).parents[2]
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    completed = subprocess.run(
        [sys.executable, str(root / "jmag_runtime_frontend.py"), "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    assert completed.returncode == 0
    assert "usage:" in completed.stdout.lower()
    assert "JMAG Runtime Frontend" in completed.stdout
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m unittest tests.unit.test_runtime_frontend -v
```

Expected: the subprocess test fails because the executable entrypoint and
argument parser do not yet exist.

- [ ] **Step 3: Implement the entrypoint and documentation**

Parse `--poll-ms` as a positive integer with default `2000`. Print argparse
help and exit before importing/creating Tk state when `--help` is supplied.
For normal execution, create `tk.Tk()`, instantiate `RuntimeFrontendApp`, and
call `root.mainloop()`. Catch `tk.TclError` and print a clear message to
stderr, returning exit code `1`. Add a README Quick start subsection with the
PowerShell `PYTHONPATH` and launch commands plus a warning that Force
Terminate is a last-resort operation.

- [ ] **Step 4: Run the help test to verify it passes**

Run the same unittest command. Expected: all tests pass with zero failures.

---

### Task 4: Run complete verification and live frontend smoke

**Files:**
- Verify: `jmag_runtime_frontend.py`, `tests/unit/test_runtime_frontend.py`, and existing repository tests.

- [ ] **Step 1: Run focused frontend tests**

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest tests.unit.test_runtime_frontend -v
```

Expected: all frontend tests pass.

- [ ] **Step 2: Run syntax validation**

```powershell
python -c "import ast, pathlib; ast.parse(pathlib.Path('jmag_runtime_frontend.py').read_text(encoding='utf-8')); print('ast_parse_ok')"
```

Expected output: `ast_parse_ok`.

- [ ] **Step 3: Run the complete unittest suite**

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests -v
```

Expected: exit code 0 and zero failures. Real-JMAG tests may remain skipped
when the live-smoke environment variable is not enabled.

- [ ] **Step 4: Launch the real frontend**

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python .\jmag_runtime_frontend.py
```

Confirm that the window opens, the table refreshes, and the log reports either
discovered targets or a structured process-discovery diagnostic. Close the
frontend normally. Do not invoke Force Terminate during this smoke test.

- [ ] **Step 5: Inspect the final diff**

```powershell
git status --short
git diff -- jmag_runtime_frontend.py tests/unit/test_runtime_frontend.py README.md
```

Confirm that only the requested frontend files and documentation changed; do
not stage or overwrite unrelated existing user changes.
