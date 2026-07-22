# JMAG Project Lifecycle Functions

This project provides reusable functions for opening, loading, saving, and
closing JMAG Designer projects. The package-level reference is
[`src/jmag_functions/PROJECT_LIFECYCLE.md`](../src/jmag_functions/PROJECT_LIFECYCLE.md).
Standalone scripts in `jmag_user_py` use `_jmag_user_env.py` to configure local
imports, while reusable lifecycle APIs live in `src/jmag_functions`.

## Lifecycle source of truth

The reusable capability state is defined only by
[`references/function-catalog.json`](../references/function-catalog.json). The
catalog lifecycle is:

```text
observed -> candidate -> verified -> approved -> stable
```

The current catalog contains verified lifecycle entries and no stable
publication. This document describes the API surface and evidence boundary; it
does not assign a separate status to individual functions.

## Functions

| Function | Purpose | Default safety behavior |
| --- | --- | --- |
| `create_application(visible=False)` | Create JMAG Designer | `False` uses batch mode; `True` creates a visible window |
| `open_project(source, visible=True, study=None)` | Create an app and load a project | One entry point for visible and batch workflows |
| `load_project(app, source, study=None)` | Load a project into an existing app | Validates the source path; optionally selects a study |
| `select_study(app, study)` | Select a study explicitly | Fails clearly when no model or study exists |
| `open_project_visible(source, study=None)` | Create a visible app and load a project | Leaves the app open for the caller |
| `save_project(app)` | Save the current project | Explicit save only |
| `save_project_as(app, target, overwrite=False)` | Save to another path | Rejects an existing target unless `overwrite=True` |
| `close_application(app, save=False)` | Close JMAG Designer | Does not save unless `save=True` |
| `load_project_copy(source, target)` | Load and save a protected copy | Never overwrites the source or an existing target |
| `find_missing_result_files(project)` | Preflight `.jplot` result references | Read-only; reports missing results before launch |
| `open_jmag_fast(project, mode=...)` | Open visibly with missing-result handling | `original`, protected `copy`, or explicitly confirmed destructive copy |

For ordinary user scripts, prefer `ProjectSession` from `jmag_functions`. It
owns the application and supports the normal `with` pattern:

```python
from jmag_functions import ProjectSession

with ProjectSession.open(
    r"C:\JMAG_Models\TestModel1.jproj",
    visible=True,
) as project:
    project.select_study("Main")
    project.save_as(r"C:\JMAG_Models\TestModel1_copy.jproj")
```

`launch_project_in_visible_designer(source)` is also available when the desired
workflow is to launch the desktop executable directly and then attach through
`JMAGContext.from_current()`.

For scripts that must avoid an interactive missing-result stop, use
`open_jmag_fast`. It preflights the sibling `.jfiles` directory and attempts to
confirm JMAG's `Missing Result Files` dialog through UI Automation or Win32.
The `copy-delete-original` mode requires `confirm_delete_original=True` and
will preserve the source if the dialog cannot be confirmed.

## Example

```python
from pathlib import Path

from jmag_functions import ProjectSession

source = Path(r"C:\JMAG_Models\TestModel1.jproj")
target = Path(r"C:\JMAG_Models\TestModel1_copy.jproj")

with ProjectSession.open(source, visible=True) as project:
    project.save_as(target)
```

## Manual validation performed

The lifecycle was tested one step at a time with user confirmation:

1. Created an empty visible JMAG Designer window.
2. Opened `TestModel1.jproj` in a separate visible window without running a study.
3. Saved a separate test copy at `C:\JMAG_Models\TestModel1_manual_step3_20260717.jproj`.
4. Saved the test copy and closed the test windows without modifying the original project.

Automated evidence is recorded in the candidate manifests under
[`docs/candidates`](candidates) and in the TestModel1 report. The current
repository verification suite covers fake-object contracts and offline safety;
real-study evidence remains separate from the repeatable offline verification
command.

The lifecycle functions must therefore be read together with the catalog:
`verified` means evidence-backed but not stable, while `stable` requires fresh
verification, explicit approval, catalog/version updates, and the fail-closed
promotion workflow described in `SKILL.md`.
