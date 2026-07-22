# Repository Stabilization Checkpoint

Date: 2026-07-22
Branch: `codex/initial-platform`
Scope: documentation, classification, and consistency protection only

## Current truth

The offline executor is implemented for the explicit 2D V-IPM
DesignSpec. The offline design executor validates and plans the specification,
executes the complete workflow through deterministic Mock adapters, and writes
a reproducible run
manifest and result bundle without importing `designer`.

`execute-design` is currently Mock-only. Its CLI exposes only
`--adapter mock`; no live Geometry, Study, solver, result, or Scheduler adapter
is implemented. Mock metrics and reports must remain labeled as offline or
mock-only evidence.

`inspect-jmdl` is currently missing. The source fixture
`Test_JMAG_Model_Files.jmdl` is present locally and its hash/ZIP integrity has
been checked, but no JMDL parser, discovery module, CLI command, fixture test,
or Phase 1 inventory/report pipeline is present in this checkout.

The Geometry Editor parameterized-circle work has partial live evidence. The
saved JMAG artifact contains the expected sketch and `radii1 = 45` parameter,
but the repository does not yet contain a repeatable execution transcript,
run manifest, and reopen verification that together prove the workflow.

## Capability lifecycle

[`references/function-catalog.json`](../references/function-catalog.json) is
the sole source of truth for reusable capability status. It currently contains
verified entries and no stable entries. Candidate manifests under
[`docs/candidates`](candidates) provide evidence records; `observed` entries
remain outside the catalog until independently verified.

Promotion remains fail-closed:

```text
observed -> candidate -> verified -> approved -> stable
```

This checkpoint performs no promotion and does not change the catalog.

## Verification baseline

The current baseline is:

- system Python full suite: passing; the real-JMAG lifecycle test and optional
  PySide6 tests remain skipped in offline mode;
- `.\jmag-skill.cmd verify`: passing; the same live/optional tests remain
  skipped in offline mode;
- JMAG 25.1 bundled Python full suite: passing; the same live/optional tests
  remain skipped unless explicitly enabled;
- real-JMAG lifecycle test is skipped unless `JMAG_REAL_SMOKE=1` is explicitly
  enabled;
- three PySide6 tests are skipped when the optional GUI dependency is absent.

The first non-elevated test attempt hit Windows Temp-directory `WinError 5`;
the same tests passed after using a permitted temporary directory. This is an
environment restriction, not a repository assertion result.

## Repository classification

| Class | Meaning in this checkout | Examples |
| --- | --- | --- |
| A | Production source, entrypoints, or design contract | `src/**`, `jmag_user_py/**`, root frontends, `examples/design_specs/**` |
| B | Test source or test fixture | `tests/**` |
| C | Maintained documentation or lifecycle metadata | `README.md`, `docs/*.md`, candidate manifests, plans/specs |
| D | Reproducible live JMAG evidence | TestModel1 report/probe, Geometry Editor smoke archives |
| E | Generated output, cache, or local test runtime | `artifacts/**`, `tmp/audit-tests-*`, `tmp/test-temp/**`, JMAG runtime logs/plots |
| F | Local/private JMAG model | `TestModel1.jproj`, `TestModel1.jfiles/**`, `Test_JMAG_Model_Files.jmdl` |
| G | Ambiguous or requiring human ownership decision | `.codex/**`, `.vscode/**`, migration baseline, legacy ownership decisions |

No files in classes F or G are deleted, moved, or overwritten by this
checkpoint. Large `.jproj`, `.jmdl`, `.jplot`, and runtime result files remain
local until their fixture/evidence role is explicitly approved.

## Next entry: Geometry live vertical slice

The next implementation entrypoint is the protected-copy smoke workflow:

1. `jmag_user_py/geometry_editor_writeback_smoke.py` - minimal Geometry Editor
   sketch creation and target-path safety;
2. `jmag_user_py/script_editor_xy_sketch.py` - parameterized XY-plane circle
   reproduction with `radii1`;
3. a future isolated live adapter and runner, after fake-object contracts and
   fresh JMAG 25.1 evidence are recorded.

Acceptance requires a new target, explicit source/target paths, a saved
transcript, a manifest naming the API call order and artifact hashes, and a
reopen check that locates the sketch through the correct hierarchy. It must not
start a Study or solver and must never overwrite the source model.

## Explicit non-goals for this checkpoint

- no JMDL parser or `inspect-jmdl` implementation;
- no live adapter;
- no Study configuration or solver integration;
- no result extraction or Scheduler submission;
- no promote, commit, reset, checkout, clean, delete, or model overwrite.
