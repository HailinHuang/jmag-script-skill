# PySide6 design frontend

This repository includes a small desktop frontend for testing the deterministic
design workflow. It currently runs the offline mock pipeline only; it does not
import `designer` or start JMAG.

## Install the frontend runtime

The frontend uses the project-local `.venv` so that the JMAG bundled Python
environment remains unchanged.

```powershell
cd C:\Codex\jmag-script-skill
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-frontend.txt
```

If the local environment was created without `pip`, use the system Python as a
fallback:

```powershell
python -m pip install --target .venv\Lib\site-packages -r requirements-frontend.txt
```

## Start the frontend

The default spec is `examples/design_specs/design_spec.yaml`.

```powershell
.\run_frontend.cmd
```

To choose a spec, output directory, or smaller test budget:

```powershell
.\run_frontend.cmd `
  --spec examples\design_specs\design_spec.yaml `
  --run-directory artifacts\runs\manual-001 `
  --maximum-cases 9
```

The run directory must not already exist. A completed run contains the result
bundle, candidate files, optimization manifest, and Markdown report.

## Interact with it

The left side is a deliberately small command window. These commands are
supported:

- `执行离线基线` or `run mock`: run the deterministic mock workflow.
- `帮助`: show the supported commands.

The right side contains four views:

- `Overview`: status, run directory, validation, and progress.
- `Metrics`: normalized raw and derived metrics.
- `Candidates`: sizing, material, optimization, and DOE data.
- `Report`: the generated Markdown design report.

The spec path and maximum DOE cases are editable before each run. The Browse
button is useful when iterating on `design_spec.yaml`.

## Test without opening a window

Use the offscreen Qt platform to verify that PySide6, Qt widgets, and the
frontend wiring are available:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\run_frontend.cmd --smoke
```

Expected output begins with:

```text
frontend_smoke_ok tabs=4
```

Run the frontend-specific tests with the project-local Python:

```powershell
$env:PYTHONPATH = "src"
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m unittest `
  tests.unit.test_frontend_model `
  tests.unit.test_frontend_qt -v
```

The repository's normal `jmag-skill.cmd verify` uses the JMAG bundled Python;
it runs the Qt-independent frontend tests and skips the PySide6 tests when
that runtime cannot import PySide6.

## Stage-based Agent flow

Click `Start Agent Flow` to create a new session. The recommended test path is:

1. Click `Load spec into Agent` to seed the conversation from the example spec.
2. Review the assumptions shown in `Design Context`.
3. Click `确认并继续` or type `确认并继续` after each stage.
4. Watch the middle panel for the current capability and next available actions.
5. Use `重新执行当前步骤` when testing a stage in isolation.
6. Inspect `Event Log`, `Metrics`, `Candidates`, and `Report` after completion.

The Agent flow supports abstract Mock topologies such as SPM, V-IPM, IPM, and
SynRM. V-IPM additionally uses the detailed existing V-IPM Mock path. The
session artifacts are written under `artifacts/runs/agent-session-<id>` and
are never written over an existing session.

The flow is rule-based and deterministic. It is a frontend/workflow test
surface, not a live LLM Agent and not a live JMAG simulation.

## Where to modify the frontend

- `src/jmag_skill/frontend/model.py`: command vocabulary and display shaping.
- `src/jmag_skill/frontend/runner.py`: frontend-to-workflow service boundary.
- `src/jmag_skill/frontend/app.py`: widgets, signals, worker thread, and views.
- `jmag_design_frontend.py`: stable entry point.

To add a new interaction, add a command classification test first, implement
the service action in `runner.py`, then connect its result to a new view or
existing tab in `app.py`. Keep JMAG-specific calls outside this package until
the corresponding live capability has evidence and a dedicated smoke test.
