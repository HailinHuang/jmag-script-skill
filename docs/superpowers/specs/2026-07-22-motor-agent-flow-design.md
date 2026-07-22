# Motor Preliminary Design Agent and PySide6 Mock Flow

## Purpose

The desktop frontend now supports a deterministic, stage-based Agent flow for
motor preliminary design. It does not require an LLM and does not start JMAG.
The flow exposes the current capability, completed work, assumptions, and
next available actions after every stage.

All topologies can complete an abstract synthetic Mock flow. V-IPM additionally
uses the existing detailed Mock Geometry, Study, Solver, and Results boundaries.
Every result is labelled `mock_only` or `synthetic_mock`.

## Stage model

```text
requirements
-> operating_points
-> topology_screening
-> preliminary_sizing
-> material_screening
-> winding_electrical
-> design_confirmation
-> geometry_mock
-> study_mock
-> solve_mock
-> results_mock
-> candidate_report
-> completed
```

Each stage has one of:

```text
pending | running | completed | blocked | failed | stale
```

The user must confirm the next action before a stage is executed. Missing
requirements block the current stage and are returned as named fields. A
changed input marks the affected stage and all downstream stages as `stale`.
The session then restarts from the earliest affected stage.

## Agent service contract

The flow is implemented by `AgentFlowService` in
`src/jmag_skill/frontend/flow.py`:

```python
session = service.create_session()
service.handle_intent(session.session_id, "start_design")
service.handle_intent(session.session_id, "update_context", payload)
service.continue_stage(session.session_id)
service.retry_stage(session.session_id)
service.get_capabilities(session.session_id)
service.get_next_actions(session.session_id)
```

`DesignSession` stores the session identifier, stage state, design context,
confirmed fields, assumptions, events, stage outputs, artifacts, and evidence
status. The session is persisted under a new directory in `artifacts/runs`.

The supported fixed intents are:

```text
start_design
update_context
continue_stage
retry_stage
view_capabilities
view_context
view_results
```

The PySide6 UI also accepts the corresponding Chinese user-facing phrases.

## Capability ledger

`CapabilityRegistry` in `src/jmag_skill/frontend/capabilities.py` records:

```text
capability_id
display_name
stage
status
evidence_status
intended_jmag_functions
inputs
outputs
failure_conditions
next_actions
```

The registry distinguishes synthetic generic capabilities from the existing
detailed V-IPM Mock boundary. No capability in this feature is promoted to a
live JMAG capability.

## Session artifacts

Each session writes to a new directory:

```text
artifacts/runs/agent-session-<id>/
├── session.json
├── events.jsonl
├── stages/
│   ├── requirements.json
│   ├── operating_points.json
│   ├── topology_screening.json
│   ├── preliminary_sizing.json
│   ├── material_screening.json
│   ├── winding_electrical.json
│   ├── design_confirmation.json
│   ├── geometry_mock.json
│   ├── study_mock.json
│   ├── solve_mock.json
│   ├── results_mock.json
│   └── candidate_report.json
└── report/design_report.md
```

The stage artifacts are reproducible and contain the evidence boundary of the
stage. The generated report explicitly states that it is not a live JMAG
simulation report.

## PySide6 frontend

The main window has three columns:

1. Agent chat and command input.
2. Current stage timeline, active capability, and next actions.
3. Result tabs: Agent Flow, Event Log, Design Context, Overview, Metrics,
   Candidates, and Report.

The `Start Agent Flow` and `Load spec into Agent` controls support interactive
testing. `Run Mock Baseline` remains as a direct shortcut to the existing
`OfflineFrontendService`.

Agent stage execution and direct baseline execution use Qt worker threads so
the main window remains responsive.

## Test and acceptance contract

Pure Python tests cover state transitions, missing fields, stale propagation,
capability records, retry behavior, abstract topology artifacts, and the
detailed V-IPM Mock path.

Qt tests run with `QT_QPA_PLATFORM=offscreen` and cover the seven result tabs,
stage view, capability view, next-action view, and flow event rendering.

The complete feature must pass:

```powershell
.\jmag-skill.cmd verify
$env:PYTHONPATH = "src"
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m unittest `
  tests.unit.test_frontend_model `
  tests.unit.test_frontend_flow `
  tests.unit.test_frontend_qt -v
```

No test in this feature starts JMAG or imports `designer` from the frontend
flow, session, capability, or abstract Mock modules.

## Future JMAG implementation boundary

The Agent flow is intentionally independent of live JMAG. Future adapters can
replace the Mock capability implementations behind the same stage outputs.
The live sequence remains:

```text
bounded Help or recorded evidence
-> fake-object contract test
-> isolated JMAG 25.1 smoke
-> verified candidate
-> explicit approval
-> stable capability
```

The existing `docs/JMAG_CAPABILITY_BUILD_PLAN.md` remains the source of truth
for that live capability work.
