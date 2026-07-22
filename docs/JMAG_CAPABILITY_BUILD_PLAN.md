# JMAG Capability Build Plan

## Boundary

The Python library is the only functional source of truth for this commit.
`src/jmag_skill/executor/`, `src/jmag_skill/offline/`,
`src/jmag_skill/frontend/`, `examples/`, and the mock components historically
associated with those paths are not present. This is a future architecture
plan, not evidence of a current implementation.

## Planned architecture

The intended sequence is:

```text
validate -> resolve -> plan -> geometry -> study -> solve -> extract -> report
```

Each stage is planned until anchored JMAG Designer 25.1 evidence, fake-object
tests, and an isolated verification establish it. Do not claim a solver,
Scheduler, result pipeline, or offline executor is implemented merely because
this plan names it.

## Future order

1. Protected project opening and a small Geometry vertical slice.
2. Parameter and explicit case execution evidence.
3. A V-IPM reference workflow, clearly labeled as reference work.
4. Only then consider executor, offline, frontend, and report layers.

Capability promotion remains explicit: public Python exports do not become
stable Agent capabilities without the catalog lifecycle and approval gates.
