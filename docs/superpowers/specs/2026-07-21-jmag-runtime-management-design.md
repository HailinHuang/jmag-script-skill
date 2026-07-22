# JMAG Runtime Management Design

## Goal

Add a reusable runtime-management capability under `jmag_functions` that can
inspect JMAG Designer and Scheduler activity, control visible window state,
cancel selected or all jobs, and optionally save and close attached Designer
applications.

## Scope

The first version covers four runtime sources:

- the currently attached JMAG Designer `Application` object;
- Scheduler `JobApplication` objects supplied by the caller;
- Windows JMAG processes discovered from process metadata;
- project paths ending in `.jproj` associated with discovered Designer
  processes.

The feature distinguishes these actions:

- cancel a calculation/job;
- close a Designer application, with an optional save;
- change a Windows window between foreground and minimized state;
- terminate a process as an explicit, opt-in last resort.

It does not silently save, close, or terminate anything during inspection.

## Architecture

`src/jmag_functions/runtime.py` owns the source-of-truth orchestration. It
uses small adapters so tests can provide fake JMAG objects and fake process
records without starting JMAG or Windows subprocesses.

`JMAGRuntimeManager` accepts an optional attached Designer application, an
optional Scheduler object, and an optional process provider. Its `refresh()`
method produces immutable runtime records. Action methods consume those
records or stable target IDs and return per-target results rather than
stopping at the first error.

The default Windows process provider uses PowerShell's
`Get-CimInstance Win32_Process` to retrieve process name, PID, command line,
parent PID, and executable path. Window operations use an injectable window
controller; the default controller is a small `ctypes` wrapper around
`ShowWindow` and `SetForegroundWindow`.

## Public API

```python
from jmag_functions.runtime import JMAGRuntimeManager

manager = JMAGRuntimeManager(app=app, scheduler=scheduler)
snapshot = manager.refresh()
results = manager.stop_all_jobs(save=False)
manager.save_and_close_all_designers()
```

The manager exposes:

- `refresh()` and `snapshot` for one-shot state inspection;
- `watch(interval=2.0, timeout=None)` for bounded polling;
- `bring_to_front(target)` and `minimize_to_background(target)`;
- `stop_selected_jobs(targets, save=False)` and `stop_all_jobs(save=False)`;
- `close_selected_designers(targets, save=False)` and
  `close_all_designers(save=False)` and `save_and_close_all_designers()`;
- `terminate_selected_processes(targets)` with explicit opt-in semantics.

Top-level convenience functions use the same manager implementation and are
exported from `jmag_functions` for direct use.

## Safety and error handling

- Inspection is read-only and never calls `Save`, `Cancel`, `Quit`, or process
  termination.
- A Designer save is attempted only when the target is attached to the
  supplied `Application` object. If saving fails, that target is not closed
  and the result records the exception.
- A Scheduler target uses `GetJobByFolder(folder).Cancel()` when the supplied
  Scheduler supports it. A discovered process without an attached API object
  is not safely cancellable and returns an actionable failure.
- One target failure does not prevent other targets from being attempted.
- Process termination requires `force=True` at the lower-level operation and
  is not part of `stop_all_jobs` or save-and-close operations.
- Unsupported platforms or unavailable Windows APIs produce structured
  failures instead of import-time errors.

## Testing

Unit tests cover process parsing, target merging, status and progress
reporting, foreground/minimize delegation, selected/all cancellation,
save-before-close behavior, per-target error aggregation, and refusal to
terminate without explicit force authorization.

The test suite uses fake objects and injected providers. A real JMAG smoke
test is optional because process discovery and window control are host-level
concerns; no live process is stopped by automated tests.
