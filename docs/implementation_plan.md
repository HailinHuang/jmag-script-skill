# Repository Stabilization and Geometry Vertical Slice Plan

This document is the maintained implementation plan for the current checkout.
It replaces the missing `docs/implementation_plan.md` referenced by the older
JMDL discovery plan. JMDL discovery remains a separate future workstream and
is not silently treated as implemented here.

## Completed checkpoint: repository stabilization

- classify all changed and untracked paths without deleting or moving them;
- record current source-of-truth boundaries in `docs/current_status.md`;
- align README and lifecycle documentation with the catalog and CLI;
- add a behavior test for documentation and capability-boundary drift;
- ignore only confirmed generated test/runtime directories;
- run system Python, bundled Python, CLI help, Mock smoke, and static checks;
- do not change `references/function-catalog.json` or promote any capability.

## Current implementation boundary

The offline executor is complete for the explicit 2D V-IPM DesignSpec:

```text
validate -> resolve -> plan -> geometry(mock) -> study(mock)
         -> solve(mock) -> extract(mock) -> report(offline)
```

`execute-design` accepts only `MockJmagAdapter`. Its geometry, study, solve,
and result boundaries are mock-only. The result bundle is a deterministic
software fixture and must carry its mock/offline provenance.
There is no `inspect-jmdl` command, no live executor adapter, and no live
Study or solver implementation in this plan.

## Next phase: Geometry live vertical slice

**Entry files:**

- `jmag_user_py/geometry_editor_writeback_smoke.py`;
- `jmag_user_py/script_editor_xy_sketch.py`;
- `docs/JMAG_CAPABILITY_BUILD_PLAN.md` for the evidence gate;
- `references/help-index.jsonl` and installed JMAG 25.1 Help for API anchors.

**Required sequence:**

1. write or refine fake-object contract tests for the minimal Geometry Editor
   interface;
2. run a single isolated live smoke against a newly created target;
3. record the exact API call order, JMAG version, source/target paths, cleanup,
   target hash, and artifact manifest;
4. inspect the saved Geometry Editor hierarchy and prove the parameterized
   sketch survives reopen;
5. review the evidence without changing catalog state.

**Acceptance gate:** the source model is byte-for-byte unchanged, an existing
target is rejected, the new target can be reopened, the sketch and named
parameter are found through a stable hierarchy, and no Study or solver runs.

## Later phases, not authorized by this checkpoint

- parameterized V-IPM geometry beyond the minimal smoke;
- live magnetic-transient Study configuration;
- solver submission, status, cancellation, resume, or Scheduler integration;
- live result extraction and report provenance;
- JMDL archive parser, graph, semantic analysis, or `inspect-jmdl` CLI;
- catalog promotion or stable publication.

## Verification commands

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests -v
.\jmag-skill.cmd verify
& "C:\Program Files\JMAG-Designer25.1\python3.12\python.exe" -m unittest discover -s tests -v
.\jmag-skill.cmd --help
.\jmag-skill.cmd execute-design examples\design_specs\design_spec.yaml --adapter mock --run-directory <new-run-directory>
python -m compileall -q src tests jmag_user_py
```

All generated run directories must be new and local. The commands above must
not set `JMAG_REAL_SMOKE=1`, invoke `promote`, or target an original model.
