# JMAG Script Skill

This repository provides bounded JMAG Help retrieval, a reusable Python
capability library, candidate lifecycle enforcement, and locked project
synchronization for JMAG Designer 25.1.

## Quick start

```powershell
.\jmag-skill.cmd build-index
.\jmag-skill.cmd search "set equation parameter"
.\jmag-skill.cmd help "Study RunAllCases" --max-topics 3
.\jmag-skill.cmd verify
```

The checked-in launcher uses the JMAG 25.1 bundled Python, so no global Python
installation is required.

## Deterministic design executor (mock slice)

The first executor slice validates and plans the explicit 2D V-IPM example,
then runs the complete workflow against a deterministic mock adapter. It does
not import `designer` or start JMAG.

```powershell
.\jmag-skill.cmd validate-design examples\design_specs\design_spec.yaml
.\jmag-skill.cmd plan-design examples\design_specs\design_spec.yaml
.\jmag-skill.cmd execute-design examples\design_specs\design_spec.yaml --adapter mock
.\jmag-skill.cmd execute-offline examples\design_specs\design_spec.yaml --submit-mock-job
.\jmag-skill.cmd size-design --rated-power-kw 110 --rated-speed-rpm 3000
.\jmag-skill.cmd prepare-optimization examples\design_specs\design_spec.yaml
.\jmag-skill.cmd generate-report artifacts\runs\<run-id>
```

Use `--run-directory` to choose a new output directory. Existing run
directories are rejected. A completed mock run contains the input and resolved
specifications, execution plan, stage events, manifests, a mock project file,
and `result_bundle.json`.

Offline sizing, material screening, optimization preparation, Mock Scheduler
submission, result normalization, and report generation are described in
[`docs/JMAG_CAPABILITY_BUILD_PLAN.md`](docs/JMAG_CAPABILITY_BUILD_PLAN.md).
Their evidence status is offline or mock-only until the corresponding isolated
JMAG 25.1 capability has been verified.

## JMAG Runtime Frontend

The repository-root `jmag_runtime_frontend.py` provides a dependency-free
Tkinter console for inspecting JMAG Designer, Scheduler, and related Windows
processes. It can bring windows forward, minimize them, cancel attached jobs,
and save/close attached Designer instances. Process termination is a separate
last-resort action that requires an explicit confirmation.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python .\jmag_runtime_frontend.py
```

Use `python .\jmag_runtime_frontend.py --help` to view the polling option
without starting Tkinter or touching JMAG.

## Capability status

[`references/function-catalog.json`](references/function-catalog.json) is the
single source of truth for reusable capability lifecycle state. It currently
contains verified entries and no stable entries; do not infer status from this
README or from a candidate filename. Verified functions remain excluded from
default search and project synchronization until stable publication.

The offline design executor is implemented for the explicit 2D V-IPM
DesignSpec. `execute-design` currently supports only `MockJmagAdapter`; its
geometry, study, solve, and result records are mock-only and do not claim live
JMAG behavior.

The read-only JMDL Phase 1 is not implemented in this checkout. There is no
`inspect-jmdl` CLI command, JMDL parser, or JMDL inventory/report test suite.
The local `Test_JMAG_Model_Files.jmdl` remains a protected fixture candidate,
not a live mutation target.

The Geometry Editor parameterized-circle evidence is partial: a saved JMAG
artifact contains the expected sketch and design parameter, but a repeatable
transcript, manifest, and reopen proof are still required.

See [`docs/current_status.md`](docs/current_status.md) and
[`docs/implementation_plan.md`](docs/implementation_plan.md) for the current
checkpoint and the next Geometry live vertical slice.

`orchestration.evaluate_cases` is a newly refactored, observed candidate. It is
kept out of the catalog and top-level `jmag_functions` exports until independent
real-study evidence exists. Import it directly when evaluating it in a project.

## Function library layout

| Category | Location | Responsibility |
| --- | --- | --- |
| Session | `src/jmag_functions/session.py` | Bind and validate the application, model, study, and design table through `JMAGContext`. |
| Design table | `src/jmag_functions/design_table.py` | Set one or multiple equation parameters after full prevalidation. |
| Results | `src/jmag_functions/results.py` | Read scalar equation parameters or response values. |
| Study execution | `src/jmag_functions/study.py` | Run all or selected cases with an explicit result lifecycle policy. |
| Project safety | `src/jmag_functions/project.py` | Load/save protected copies, preflight missing results, and fast-open visible Designer projects with explicit copy policies. |
| Inventory | `src/jmag_functions/inventory.py` | Enumerate Design Table parameters and available Equation metadata. |
| Exports | `src/jmag_functions/exports.py` | Export Design Table, response values, or full result tables with explicit policies. |
| Runtime management | `src/jmag_functions/runtime.py` | Inspect JMAG Designer/Scheduler activity, switch windows, cancel selected/all jobs, and save/close attached Designer instances. |
| Orchestration candidate | `src/jmag_functions/orchestration.py` | Compose set, run, and read operations without embedding project constants. |
| Skill lifecycle | `src/jmag_skill/` | Search, Help retrieval, inspection, verification, promotion, synchronization, and rollback. |

The legacy `jmag_user_py/users/jmag_operation.py` remains project code. Reusable
behavior belongs in the focused modules above; project paths, study names,
machine constants, optimizer settings, and assignment rules stay outside the
function library.

## One-click GitHub publishing

Double-click `publish.cmd` to run the guarded publish workflow. It checks the
GitHub remote and authentication, runs the offline test suite, stages only
allowed source/documentation/test paths, excludes local JMAG projects and
temporary artifacts, writes `docs/PUBLISH_STATUS.md`, pushes the current branch,
and opens a Draft PR. If any gate fails, no commit or push is performed; the
report records eligible files, blocked files, and incomplete conditions.

Runtime inspection is read-only. Normal stop functions use JMAG cancellation
APIs; process termination is a separate explicit operation and is never part
of `stop_all_jmag_jobs` or save-and-close workflows.

```python
from jmag_functions import JMAGRuntimeManager

runtime = JMAGRuntimeManager(app=app, scheduler=scheduler, scheduler_folders=folders)
for target in runtime.refresh().targets:
    print(target.target_id, target.kind, target.project_path, target.status, target.progress)

runtime.bring_to_front("designer:99")
runtime.minimize_to_background("designer:99")
runtime.stop_selected_jobs(["scheduler:C:\\Runs\\job.jfiles", "designer:99"])
runtime.save_and_close_all_designers()
```

## Behavior contracts

- Public case numbers are one-based; conversion to JMAG's zero-based index is
  centralized in `JMAGContext.case_index`.
- `set_parameter` and `set_parameters` never delete results. Multiple names are
  resolved before the first write to prevent partial updates.
- `run_cases` follows the approved initial contract and defaults to
  `clear_results=True`; pass `clear_results=False` to preserve existing results.
  Use `apply_cad_parameters=True` when changed parameters must be applied before
  execution.
- `load_project_copy` rejects missing sources, existing targets, missing target
  directories, and source overwrite. It always creates and owns an isolated
  JMAG application, so it cannot replace a caller's current project.
- Export functions reject existing files by default. `export_result_tables`
  requires an explicit `Step`, `Time`, `Angle`, or `Distance` axis.
- `inventory_design_table` records broken or unnamed Equation wrappers as an
  `equation_error` without discarding the rest of the inventory.
- `evaluate_cases` deliberately has no default for `clear_results`, so a caller
  must choose the destructive result policy at every workflow call.
- `get_values` returns a name-to-value dictionary for one case. It does not hide
  multi-case aggregation or silently sum results.
- No function opens a project from a hard-coded path or assumes a study name,
  response name, winding layout, or optimizer configuration.

## Composed evaluation workflow

```python
from jmag_functions import JMAGContext
from jmag_functions.orchestration import evaluate_cases

context = JMAGContext.from_current(study="main")
results = evaluate_cases(
    context,
    {"speed": 2500, "angle": 20},
    ["torque", "voltage"],
    [1, 3],
    clear_results=True,
)
```

The example's study, parameter names, response names, values, and cases are
project configuration rather than defaults in the reusable function.
`evaluate_cases` prevalidates all cases and parameter names before its first
write, runs only the requested cases, restores the original current case, and
returns `{case: {name: value}}`.

## Protected project-copy workflow

```python
from pathlib import Path

from jmag_functions import (
    JMAGContext,
    export_case_values,
    export_design_table,
    export_result_tables,
    inventory_design_table,
    load_project_copy,
    run_cases,
    set_parameter,
)

source = Path("model.jproj")
copy = Path("output/model_test.jproj")

with load_project_copy(source, copy) as project:
    context = JMAGContext.from_current(project.app, study="study-name")
    parameters = inventory_design_table(context, case=1)
    set_parameter(context, "parameter-name", 12, case=1)
    run_cases(
        context,
        cases=1,
        clear_results=True,
        apply_cad_parameters=True,
    )
    export_design_table(context, copy.parent / "design_table.csv")
    export_case_values(context, copy.parent / "case_values.csv")
    export_result_tables(
        context, copy.parent / "result_tables.csv", axis="Step"
    )
    project.save()
```

Paths, study and parameter names, cases, values, result axes, and destructive
result policy remain caller configuration. TestModel1's
`Step = Div / Div_Period * 1.5 + 1` conversion is intentionally not reusable.

## TestModel1 real-project evidence

[`docs/TESTMODEL1_FUNCTION_TEST_REPORT.md`](docs/TESTMODEL1_FUNCTION_TEST_REPORT.md)
records a protected-copy test against JMAG Designer 25.1. The run enumerated
126 Design Table parameters, preserved the model's existing Step equation,
changed `Div` from 60 to 8 to reduce 90 transient intervals to 12, solved case
1, and exported response and full result tables. The source project was not
saved. The recommended reusable functions are cataloged as `verified`, not
`stable`; no stable publication was performed.

## Legacy migration map

| Legacy function | Reusable replacement | Intentional change |
| --- | --- | --- |
| `initialize_jmag`, `_activate_study` | `JMAGContext.from_current`, `JMAGContext.activate` | Session ownership and study binding are explicit. |
| `_normalize_cases`, `run_case` | `run_cases` | Cases are validated consistently and the original current case is restored. |
| `_parameter_index` | `JMAGContext.parameter_index` | Parameter lookup has one implementation. |
| `_read_scalar`, `get_data` | `get_value` | One call reads one named scalar from one case. |
| `get_datas` | `get_values` | Returns a dictionary instead of a position-dependent list. |
| `set_para`, `set_paras` | `set_parameter`, `set_parameters` | Setters have no hidden `DeleteResult` side effect. |
| `get_datas_set_paras` | `orchestration.evaluate_cases` | The set-run-read lifecycle and result-clearing decision are explicit. |
| `set_para_leave_result` | No alias | Combine `set_parameter` with an explicit lifecycle only after a project proves the desired stale-result behavior. |
| `open_file`, `delete_result` | No reusable counterpart yet | Project opening and result deletion need bounded Help evidence and real-study smoke before extraction. |

The legacy `get_data(name, cases=[...])` summation behavior is not preserved.
Use the explicit per-case dictionary returned by `evaluate_cases`, then perform
the required aggregation in project code where its meaning is visible.

## PySide6 design frontend

For a convenient interactive test surface, run:

```powershell
.\run_frontend.cmd
```

The frontend provides a command window plus Overview, Metrics, Candidates,
and Report views. It now also provides a stage-based preliminary-design Agent
flow with dynamic capability and next-action panels. It calls the offline mock
workflow and does not start JMAG. See [`docs/FRONTEND_USAGE.md`](docs/FRONTEND_USAGE.md)
and [`docs/superpowers/specs/2026-07-22-motor-agent-flow-design.md`](docs/superpowers/specs/2026-07-22-motor-agent-flow-design.md)
for installation, staged interaction, artifact layout, and extension points.

## Candidate and promotion boundary

Candidate inspection never changes the stable library. The lifecycle is
`observed -> candidate -> verified -> approved -> stable`. Promotion requires
verified evidence plus explicit approval, followed by a fresh verification
before stable publication.

The current `promote` command performs only the explicit approval transition.
Stable publication remains fail-closed until a transactional verifier can run
RED/GREEN evidence, real JMAG study smoke, catalog/version update, commit, and
REM as one operation.

## Project synchronization and rollback

Project synchronization creates a lock file and copies only requested stable
modules and dependencies. It does not initialize Git in the target project.

Use `jmag-skill rollback <project>` to restore the most recent function-lock
snapshot created before an update.
