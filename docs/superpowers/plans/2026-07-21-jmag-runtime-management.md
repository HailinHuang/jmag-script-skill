# JMAG Runtime Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe inspection and control of attached JMAG Designer applications, Scheduler jobs, and discovered Windows JMAG processes.

**Architecture:** Implement one adapter-driven `JMAGRuntimeManager` in `src/jmag_functions/runtime.py`. Keep JMAG API calls, Windows process discovery, and window control behind injectable interfaces so all behavior can be verified with fake objects. Export the manager and convenience functions from `jmag_functions`.

**Tech Stack:** Python 3.10+, standard-library dataclasses, subprocess, ctypes, unittest, and existing JMAG Designer API objects.

## Global Constraints

- Inspection must never mutate JMAG projects or processes.
- Normal cancellation must use `Application.CancelProcess()` or Scheduler `Job.Cancel()`.
- Saving and closing must fail closed when the target is not attached or saving raises.
- Process termination must require explicit authorization and must not be used by normal stop-all operations.
- Do not add runtime dependencies.
- Preserve existing uncommitted user files and modify only feature-specific files.

---

### Task 1: Add process and runtime data contracts

**Files:**
- Create: `src/jmag_functions/runtime.py`
- Test: `tests/unit/test_runtime.py`

**Interfaces:**
- Produce `ProcessRecord`, `RuntimeTarget`, `RuntimeSnapshot`, and `OperationResult` dataclasses.
- Produce `parse_jproj_path(command_line)`, which returns a normalized `Path | None`.
- Produce `merge_runtime_targets(attached, scheduler, processes)`, which deduplicates by target ID.

- [ ] **Step 1: Write the failing tests**

```python
def test_parse_jproj_path_extracts_quoted_path():
    record = parse_jproj_path(r'"C:\\Models\\motor test.jproj" -g')
    assert record == Path(r'C:\\Models\\motor test.jproj').resolve()


def test_merge_runtime_targets_keeps_attached_target_and_process_metadata():
    attached = [RuntimeTarget("designer:123", "designer", 123, Path("m.jproj"), "running", True)]
    processes = [ProcessRecord("designer.exe", 123, r'"C:\\Models\\m.jproj"', 1, r'C:\\designer.exe')]
    merged = merge_runtime_targets(attached, [], processes)
    assert len(merged) == 1
    assert merged[0].pid == 123
    assert merged[0].project_path == Path(r'C:\\Models\\m.jproj').resolve()
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `$env:PYTHONPATH=(Join-Path (Get-Location) 'src'); python -m unittest tests.unit.test_runtime -v`

Expected: collection fails because `jmag_functions.runtime` and its symbols do not yet exist.

- [ ] **Step 3: Write the minimal implementation**

Use frozen dataclasses and stable IDs. Define `RuntimeTarget` fields as
`target_id`, `kind`, `pid`, `project_path`, `status`, `progress`,
`window_handle`, `attached`, and `metadata`. Return a new merged list sorted
by `(kind, target_id)` and keep the attached target as the source of JMAG
control capabilities.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `$env:PYTHONPATH=(Join-Path (Get-Location) 'src'); python -m unittest tests.unit.test_runtime -v`

Expected: the new tests pass with zero failures.

### Task 2: Implement read-only process discovery and status refresh

**Files:**
- Modify: `src/jmag_functions/runtime.py`
- Test: `tests/unit/test_runtime.py`

**Interfaces:**
- Consume the data contracts from Task 1.
- Produce `WindowsProcessProvider.records()` and `JMAGRuntimeManager.refresh()`.

- [ ] **Step 1: Write the failing tests**

```python
def test_refresh_reports_attached_designer_running_state_and_path():
    app = FakeApp(path=r"C:\\Models\\motor.jproj", running=True)
    snapshot = JMAGRuntimeManager(app=app, process_provider=FakeProvider([])).refresh()
    target = snapshot.by_kind("designer")[0]
    assert target.project_path == Path(r"C:\\Models\\motor.jproj").resolve()
    assert target.status == "running"
    assert target.attached is True


def test_refresh_is_read_only():
    app = FakeApp(path=r"C:\\Models\\motor.jproj", running=True)
    JMAGRuntimeManager(app=app, process_provider=FakeProvider([])).refresh()
    assert app.calls == ["GetProjectPath", "HasRunningProcess"]
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `$env:PYTHONPATH=(Join-Path (Get-Location) 'src'); python -m unittest tests.unit.test_runtime -v`

Expected: the new refresh tests fail because the manager has no refresh implementation.

- [ ] **Step 3: Write the minimal implementation**

Implement `WindowsProcessProvider` with a single PowerShell query returning
JSON and convert only processes whose names contain `designer` or `scheduler`.
Catch command, JSON, and platform errors and return an empty list plus a
diagnostic in snapshot metadata. Read attached Designer status using only
`GetProjectPath()`, `HasRunningProcess()`, and optional `GetProcessId()` when
available. Query Scheduler folders supplied by the caller and use
`GetJobByFolder(folder)`, `Status()`, and `PercentComplete()` when available.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `$env:PYTHONPATH=(Join-Path (Get-Location) 'src'); python -m unittest tests.unit.test_runtime -v`

Expected: all runtime discovery tests pass.

### Task 3: Implement window control and safe action methods

**Files:**
- Modify: `src/jmag_functions/runtime.py`
- Test: `tests/unit/test_runtime.py`

**Interfaces:**
- Consume `RuntimeTarget` IDs from `RuntimeSnapshot`.
- Produce `OperationResult` lists from `bring_to_front`, `minimize_to_background`, `stop_selected_jobs`, `stop_all_jobs`, `close_selected_designers`, `close_all_designers`, and `save_and_close_all_designers`.

- [ ] **Step 1: Write the failing tests**

```python
def test_stop_selected_cancels_scheduler_job_and_designer_process():
    app = FakeApp(path=r"C:\\Models\\motor.jproj", running=True)
    scheduler = FakeScheduler({r"C:\\Runs\\job.jfiles": FakeJob()})
    manager = JMAGRuntimeManager(
        app=app,
        scheduler=scheduler,
        scheduler_folders=[r"C:\\Runs\\job.jfiles"],
        process_provider=FakeProvider([]),
    )
    results = manager.stop_selected_jobs(["scheduler:C:\\Runs\\job.jfiles", "designer:attached"])
    assert all(result.ok for result in results)
    assert scheduler.jobs[r"C:\\Runs\\job.jfiles"].cancelled is True
    assert app.cancel_count == 1


def test_save_and_close_does_not_quit_when_save_fails():
    app = FakeApp(path=r"C:\\Models\\motor.jproj", running=False, save_error=OSError("locked"))
    result = JMAGRuntimeManager(app=app, process_provider=FakeProvider([])).save_and_close_all_designers()[0]
    assert result.ok is False
    assert app.quit_count == 0


def test_window_operations_delegate_to_injected_controller():
    controller = FakeWindowController()
    manager = JMAGRuntimeManager(app=FakeApp(), window_controller=controller, process_provider=FakeProvider([]))
    manager.bring_to_front("designer:attached")
    manager.minimize_to_background("designer:attached")
    assert controller.calls == [("foreground", 99), ("minimize", 99)]
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python -m unittest tests.unit.test_runtime -v`

Expected: the action tests fail because action methods are not implemented.

- [ ] **Step 3: Write the minimal implementation**

Use `Application.CancelProcess()` for attached running Designer targets and
`GetJobByFolder(folder).Cancel()` for Scheduler targets. For save-and-close,
call `Save()` first and call `Quit()` only after it succeeds. Aggregate one
`OperationResult` per target and continue after failures. The default window
controller uses `ShowWindow(SW_MINIMIZE)` and `SetForegroundWindow`; injected
controllers are used in tests.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `python -m unittest tests.unit.test_runtime -v`

Expected: all action tests pass with zero failures.

### Task 4: Add explicit force-termination boundary and public exports

**Files:**
- Modify: `src/jmag_functions/runtime.py`
- Modify: `src/jmag_functions/__init__.py`
- Modify: `README.md`
- Test: `tests/unit/test_runtime.py`

**Interfaces:**
- Produce `terminate_selected_processes(targets, *, force=False)` and
  convenience functions `list_running_jmag`, `stop_all_jmag_jobs`, and
  `save_and_close_all_jmag`.

- [ ] **Step 1: Write the failing tests**

```python
def test_process_termination_requires_explicit_force():
    provider = FakeProvider([ProcessRecord("designer.exe", 321, "", 1, "designer.exe")])
    manager = JMAGRuntimeManager(process_provider=provider, process_controller=FakeProcessController())
    result = manager.terminate_selected_processes(["process:321"])[0]
    assert result.ok is False
    assert provider.controller.calls == []
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python -m unittest tests.unit.test_runtime -v`

Expected: the test fails because force authorization is not implemented.

- [ ] **Step 3: Write the minimal implementation**

Reject `force=False` with a structured failed result and call the injected
process controller only when `force=True`. Add runtime-management imports to
`__init__.py` and add the module to the README function-library table with a
short safety note.

- [ ] **Step 4: Run the full verification suite**

Run: `$env:PYTHONPATH=(Join-Path (Get-Location) 'src'); python -m unittest discover -s tests -v`

Expected: exit code 0, zero failures; any pre-existing skipped real-JMAG test
must remain skipped for the normal Python environment.

- [ ] **Step 5: Run read-only syntax validation**

Run: `python -c "import ast, pathlib; ast.parse(pathlib.Path('src/jmag_functions/runtime.py').read_text(encoding='utf-8')); print('ast_parse_ok')"`

Expected output: `ast_parse_ok`.
