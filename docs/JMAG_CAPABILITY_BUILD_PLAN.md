# JMAG Capability Build Plan

## 1. Purpose and boundary

The offline design executor is now the source of truth for workflow shape,
specification validation, report contracts, and deterministic test fixtures.
This document defines how to replace each Mock boundary with evidence-backed
JMAG Designer 25.1 capabilities.

The live implementation must preserve this sequence:

```text
validate -> resolve -> plan -> geometry -> study -> solve -> extract -> report
```

The current offline implementation does **not** claim that Geometry Editor,
Study, Solver, Result, Optimization, or Scheduler calls have been verified in
JMAG. Mock results are fixtures for software and workflow testing only.

## 2. Current offline capability ledger

| Mock component | File | Intended JMAG capability | Current evidence |
|---|---|---|---|
| `MockGeometryEditor` | `src/jmag_skill/executor/adapters/mock_geometry.py` | Create Geometry Editor model, register parameters, build and validate V-IPM geometry, save project | `mock_only` |
| `MockStudySolver` | `src/jmag_skill/executor/adapters/mock_study.py` | Configure magnetic transient Study, materials, motion, circuit, time steps, mesh, solve, status | `mock_only` |
| `MockResultExtractor` | `src/jmag_skill/executor/adapters/mock_results.py` | Read torque, ripple, back-EMF, and loss results and export tables/waveforms | `mock_only` |
| `MockScheduler` | `src/jmag_skill/executor/adapters/mock_scheduler.py` | Submit, query, advance/cancel, and resume Scheduler jobs | `mock_only` |
| `MockJmagAdapter` | `src/jmag_skill/executor/adapters/mock_jmag.py` | Compose the previous boundaries behind the executor adapter interface | `mock_only` |

Every Mock component exposes `capability_record()`. These records describe
the intended live capability and deliberately identify the evidence status as
`mock_only`.

The complete offline composition is available through:

```powershell
.\jmag-skill.cmd execute-offline examples\design_specs\design_spec.yaml --submit-mock-job
```

It writes the Mock baseline, normalized results, sizing candidate, material
candidate list, DOE cases, optimization manifest, optional Mock Scheduler job,
and Markdown report into one new run directory.

## 3. Live capability build sequence

### Phase 0 — Evidence and runtime preflight

**Goal:** establish the smallest verified live bridge without changing the
offline path.

Tasks:

1. Use `jmag-skill search` for an existing stable capability.
2. If no stable capability matches, use bounded `jmag-skill help` retrieval with
   no more than three anchored topics.
3. Prefer a JMAG Script Recorder output or a minimal official example over
   guessed API calls.
4. Record the JMAG 25.1 bundled-Python path, application ownership, visibility,
   target path, and cleanup behavior.
5. Add fake-object contract tests before any live call.

Acceptance gate:

- The candidate has an evidence record with source anchors and observed call
  order.
- The test never opens or overwrites a user project.
- The smoke target is a new isolated project under a temporary run directory.

### Phase 1 — Geometry Editor vertical slice

**Mock source:** `MockGeometryEditor`.

Build only a minimal geometry slice first:

1. Create a new project and Geometry Editor context.
2. Create one sketch or primitive whose dimension is controlled by a named
   design parameter.
3. Save to a new target and reopen it only if the recorded evidence requires
   that check.
4. Verify the semantic parameter name and geometry object name.

Do not start with the complete V-IPM. The first live smoke should isolate
application binding, editor creation, parameter registration, save behavior,
and target-path safety.

Acceptance gate:

- The live adapter implements the same contract as `MockGeometryEditor`.
- The recorded project can be opened by JMAG 25.1.
- A second run rejects an existing target instead of overwriting it.
- The source project, if any, remains byte-for-byte untouched.

### Phase 2 — Parameterized V-IPM geometry

**Mock source:** `MockGeometryEditor.build_v_ipm()` and the explicit example at
`examples/design_specs/design_spec.yaml`.

Build in bounded increments:

1. Stator outer/inner geometry and slot profile.
2. Rotor, shaft, airgap, and V-magnet placement.
3. Stable semantic names for parts, sketches, features, and sets.
4. Design parameters and expressions with explicit units.
5. Offline nominal, minimum, maximum, and invalid-geometry validation.
6. Live verification of part existence, semantic names, and basic dimensions.

Acceptance gate:

- All geometry calls are supported by Help or recorded evidence.
- Invalid combinations are rejected before JMAG starts.
- The live smoke produces a new project and a geometry manifest.
- No Part ID is treated as a stable semantic identifier unless the evidence
  proves it stable for the target template.

### Phase 3 — Magnetic transient Study

**Mock source:** `MockStudySolver`.

Build and verify one low-cost baseline Study:

1. Resolve and assign materials by semantic name.
2. Configure rotor motion and the three-phase electrical excitation.
3. Configure time range and time-step policy from the spec.
4. Configure the smallest valid mesh policy.
5. Run preflight checks before solve.
6. Save a Study manifest before solving.

Acceptance gate:

- Study creation, material assignment, motion, circuit, time-step, and mesh
  calls each have evidence.
- The Study can be reopened or inspected after configuration.
- Solver execution does not implicitly delete existing results.
- A failed preflight prevents the live solve.

### Phase 4 — One-case solve and status

**Mock source:** `MockStudySolver.solve()` and `MockScheduler` lifecycle.

Implement a live job boundary that returns a job or case identifier instead of
blocking the conversation:

```text
submit -> status -> completed/failed -> resume or report
```

Acceptance gate:

- The live path distinguishes queued, running, completed, failed, and
  cancelled states.
- A failed case preserves its manifest and diagnostic path.
- Repeated status checks do not mutate design parameters or clear results.
- Cancellation is explicit and scoped to the selected job.

### Phase 5 — Standard result extraction

**Mock source:** `MockResultExtractor`.

Verify one result family at a time:

1. Average torque and torque ripple.
2. Phase back-EMF and waveform export.
3. Copper, iron, and magnet losses.
4. RMS current, efficiency, and any requested derived metrics.
5. CSV/table export with explicit axis and case selection.

The existing offline postprocessor remains authoritative for normalization and
physical checks. Live extraction must provide raw values and provenance; it
must not reproduce the fixed fixture values.

Acceptance gate:

- Every metric records value, unit, source Study, case, and calculation method.
- Missing results are `unavailable` with a reason, never zero.
- A real baseline is compared against tolerance bands established from a known
  JMAG project, not against the Mock fixture alone.

### Phase 6 — Optimization and Scheduler

**Mock source:** `offline.optimization` and `MockScheduler`.

Build in layers:

1. Validate variable ranges and constraints offline.
2. Generate a small deterministic DOE.
3. Run a few live cases and verify case-number semantics.
4. Compare raw and normalized results.
5. Only then connect JMAG optimization configuration.
6. Submit to Scheduler only after showing case count, license impact, and
   estimated wall time.

Acceptance gate:

- The optimization manifest is reproducible and carries template, function,
  material, and mesh versions.
- Case failures are isolated and reported according to policy.
- The user explicitly approves large or long-running submissions.
- No automatic promotion of observed functions occurs.

### Phase 7 — Report integration and capability promotion

**Offline source:** `offline.report.generate_design_report()`.

The report generator should remain JMAG-independent. The live adapter only
supplies a traceable `result_bundle.json`, raw tables, figures, and provenance.

Acceptance gate:

- Offline report tests remain green with the Mock adapter.
- Live reports clearly distinguish verified JMAG data from inferred or
  heuristic content.
- A capability moves through the repository lifecycle:

```text
observed -> candidate -> verified -> approved -> stable
```

Promotion requires explicit user approval, fresh unit/fake-object/live/behavior
verification, catalog updates, and an isolated commit.

## 4. Safety and evidence rules

- Only the future live adapter and runner may import `designer`.
- Normal validation, sizing, material screening, optimization preparation,
  report generation, and Mock Scheduler tests must not start JMAG.
- Never mutate `.jmdl` archive XML/DAT files directly.
- Never overwrite source `.jmdl` or `.jproj` files.
- Reject existing live targets by default.
- Keep paths, Study names, parameter names, response names, limits, and machine
  constants in project specifications.
- Keep live JMAG verification separate from offline test results.
- Treat material costs, heuristic sizing, and inferred labels as dated or
  illustrative until their data sources are replaced by engineering-approved
  inputs.

## 5. Recommended next implementation prompts

### Preliminary Design Agent boundary

The PySide6 frontend now has a deterministic stage-based Agent flow in
`src/jmag_skill/frontend/flow.py`. It composes preliminary sizing, material
screening, abstract geometry, Study, solve, result, and report capabilities
without starting JMAG.

The Agent capability records are deliberately separate from the live JMAG
ledger. Their status is `mock_ready` with `synthetic_mock` or `mock_only`
evidence. A future live adapter may replace one stage at a time only after the
bounded Help/recorded-evidence and isolated smoke gates above pass.

The stable live replacement order remains:

```text
mock_geometry_builder
-> mock_study_configurator
-> mock_solver
-> mock_result_extractor
-> mock_scheduler
-> report integration
```

The Agent UI must continue to display `not_verified` for these live JMAG
capabilities until they complete the repository's candidate verification and
approval lifecycle.

### Geometry prompt

> Use the bounded Help workflow and the recorded minimal editor example to
> implement only the live Geometry Editor vertical slice. Add fake-object
> tests first, isolate the target project, and do not implement Study or solve.

### Study prompt

> Starting from the verified geometry adapter, retrieve evidence for one
> magnetic transient Study, materials, motion, circuit, time steps, and mesh.
> Implement preflight and fake-object tests before one low-cost live smoke.

### Result prompt

> Starting from a verified single-case Study, add one result extractor at a
> time. Preserve raw values and provenance, compare against tolerance bands, and
> keep the existing offline normalizer and report contract unchanged.

## 6. Definition of done for the live transition

The offline phase is complete when the full offline test suite passes and every
Mock capability record is present. The live transition is complete only when:

- the first three vertical slices have independent evidence;
- source/target safety and cleanup are verified;
- one real baseline result matches expected tolerance bands;
- failure, cancellation, and resume paths are exercised;
- the capability catalog and version records are updated;
- no Mock-only result is presented as a JMAG result.
