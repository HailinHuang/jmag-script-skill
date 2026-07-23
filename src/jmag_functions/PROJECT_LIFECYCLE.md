# Project Lifecycle API

`jmag_functions.project` is the package-level API for JMAG Designer project
lifecycle operations. It contains no project-specific model names, study names,
or result settings.

## Primary entry point

```python
from jmag_functions import open_protected_project_copy

with open_protected_project_copy(
    r"C:\JMAG_Models\TestModel1.jproj",
    r"C:\JMAG_Models\TestModel1_copy.jproj",
    visible=False,
    study="Main",
    manifest_path=r"C:\JMAG_Models\m1_manifest.json",
) as project:
    project.save()
```

Leaving the `with` block closes JMAG without an implicit save. Use
`project.close(save=True)` when the close operation must save first.

## Functions

| API | Responsibility |
| --- | --- |
| `create_application(visible=False)` | Create a visible or batch JMAG application. |
| `open_project(source, visible=True, study=None)` | Create an app, load a project, and optionally select a study. |
| `load_project(app, source, study=None)` | Load into an existing app. |
| `select_study(app, study)` | Select a study in the current model. |
| `save_project(app)` | Save the current project. |
| `save_project_as(app, target, overwrite=False)` | Save to a new path; rejects overwrite by default. |
| `close_application(app, save=False)` | Close JMAG; does not save unless requested. |
| `copy_project_bundle(source, target)` | Canonical filesystem copy of `.jproj` and sibling `.jfiles`. |
| `open_protected_project_copy(source, target, ...)` | Copy first, then create and own an application that loads the target. |
| `load_protected_project_copy(app, source, target, ...)` | Copy first, then load the target into an explicitly borrowed application. |
| `load_project_copy(source, target, options=None)` | Compatibility wrapper around the canonical owned entry point. |
| `launch_project_in_visible_designer(source)` | Launch the desktop executable directly. |
| `find_missing_result_files(project)` | Preflight readable `.jplot` references and the sibling `.jfiles` directory. |
| `open_jmag_fast(project, mode=...)` | Open visibly with result preflight, copy policy, and optional dialog confirmation. |

## Legacy fast-open convenience API

`open_jmag_fast` is a legacy convenience implementation behind
`jmag_user_py/open_jmag_window.py`. It supports three explicit policies:

```python
from jmag_functions import open_jmag_fast

# Preserve and open the source project.
open_jmag_fast(r"C:\JMAG_Models\motor.jproj", mode="original")

# Open a non-overwriting copy and preserve the source.
open_jmag_fast(
    r"C:\JMAG_Models\motor.jproj",
    mode="copy",
    copy_target=r"C:\JMAG_Models\motor_automation_copy.jproj",
)

# Destructive replacement requires an explicit confirmation flag.
open_jmag_fast(
    r"C:\JMAG_Models\motor.jproj",
    mode="copy-delete-original",
    confirm_delete_original=True,
)
```

Before launching, the function checks for missing result files. If missing
results are detected, it attempts to confirm JMAG's `Missing Result Files`
dialog using UI Automation or the Windows button message API. The original is
never deleted unless `mode="copy-delete-original"` and
`confirm_delete_original=True` are both supplied; if the dialog cannot be
confirmed, deletion is aborted.

It is not an M1 protected-copy entry point. In particular, its
`copy-delete-original` mode must never be used in an M1 workflow.

## Protected-copy and ownership rules

- The canonical copy is a filesystem-level `.jproj` bundle copy, not
  `Load(source)` followed by `SaveAs(target)`.
- Sources and targets must be distinct `.jproj` paths; target `.jproj` and
  target `.jfiles` paths must be absent. Copy failures clean up only target
  paths created by the operation.
- `open_protected_project_copy` owns the application it creates and closes it
  exactly once, including after a load failure.
- `load_protected_project_copy` borrows its explicit application and never
  calls `Quit()`.
- `ManagedProjectSession.close()` does not save by default;
  `close(save=True)` saves the target before closing an owned application.
- A requested manifest rejects an existing path and records absolute paths,
  hashes, ownership, visibility, status, and errors.
- `load_project` operates on a caller-owned application and never closes it.
- Never use `save_project_as(..., overwrite=True)` unless replacing the target
  is intentional and explicitly authorized.

## Scope boundary

Study execution belongs to `jmag_functions.study`; parameter changes belong to
`jmag_functions.design_table`; result access belongs to `jmag_functions.results`.
