# JMAG Runtime Frontend Design

## Goal

Add a dependency-free Windows desktop frontend at the repository root for
viewing and controlling JMAG Designer, Scheduler, and discovered JMAG-related
processes through `jmag_functions.runtime.JMAGRuntimeManager`.

## Scope

The first version is a Tkinter application launched as
`python jmag_runtime_frontend.py`. It refreshes runtime state periodically and
shows one selectable row per runtime target. It supports bringing a target
window to the foreground, minimizing it, cancelling an attached Designer
calculation or Scheduler job, saving and closing an attached Designer, closing
an attached Designer without saving, and explicitly force-terminating a
selected process after confirmation.

Inspection is read-only. Refreshing never calls `Save`, `Cancel`, `Quit`, or
process termination. Unattached processes can be inspected and have their
windows controlled, but normal JMAG cancellation and close operations fail
closed unless `runtime.py` has an attached JMAG `Application` or Scheduler
object for the target.

## Alternatives considered

1. Tkinter with the standard library is recommended because it adds no
   dependency, runs in the existing Python environment, and is sufficient for
   a small operations console.
2. PySide6 would provide a richer interface but would add a dependency that is
   not present in `pyproject.toml` and is unnecessary for the first version.
3. A local web frontend would be easier to extend remotely but would require a
   server, browser lifecycle, and additional process boundaries.

## Architecture

`jmag_runtime_frontend.py` contains the thin executable entrypoint and
Tkinter-specific presentation. A small `RuntimeFrontendModel` in the same
file adapts `JMAGRuntimeManager` snapshots and operation results into display
rows and log messages so the UI can be tested without opening a window.

The frontend constructs a manager with its default Windows process provider,
window controller, and process controller. It accepts optional injected
manager and root objects for tests. A Tkinter timer calls `refresh()` every two
seconds, updates a `ttk.Treeview`, and preserves the selected target when it
still exists. Button handlers use the selected target ID and render each
`OperationResult` in the status log.

The process termination button is visually separated from normal controls and
requires a confirmation dialog. It calls
`terminate_selected_processes([target_id], force=True)` only after the user
confirms. The frontend never performs broad process termination implicitly.

## User interface

The window has:

- a toolbar with Refresh and polling status;
- a target table with kind, ID, PID, status, progress, project path, window
  handle, and attachment state;
- normal window and JMAG action buttons;
- a separate red-accented Force Terminate button;
- a read-only scrolling log area for operation results and diagnostics.

If a target has no window handle or is not attached to a JMAG API object, the
runtime manager returns a structured failure and the UI displays that message
instead of guessing an alternative action.

## Testing

Unit tests use fake manager/snapshot/result objects and a fake Tk root. They
cover target-row formatting, selection preservation, refresh rendering,
operation-result logging, confirmation-gated force termination, and safe
`--help` startup. A syntax check and the full existing unittest suite are run
before completion. The frontend is also launched once on Windows and then
closed by the agent after confirming that its window is responsive; no JMAG
process is terminated during automated verification.

## Run contract

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python .\jmag_runtime_frontend.py
```

The script must work on Windows with the standard Python Tkinter module and
must fail with a clear message if Tkinter is unavailable. `--help` must exit
without creating a Tk root or touching JMAG.
