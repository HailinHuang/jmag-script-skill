# Milestone 1 Existing-Project Lifecycle

Base commit: `9ce2f91c304b467fe6217accd5ee4db10494e8b0`
Runtime: JMAG Designer 25.1

## Present in this tree

- Discoverable Python packages: `jmag_functions` and `jmag_skill`.
- CLI commands: `search`, `help`, `inspect`, `promote`, `sync`, `rollback`,
  `verify`, and `build-index`.
- Runtime frontend: `jmag_user_py/jmag_runtime_frontend.py`.
- `open_protected_project_copy` and `load_protected_project_copy` create a
  filesystem-level protected `.jproj`/`.jfiles` copy, make ownership explicit,
  and can write a JSON evidence manifest.
- Capability catalog: six `verified` entries and zero `stable` entries.

Public Python exports are a library surface; they do not infer catalog status.

## Planned—not present in this tree

`src/jmag_skill/executor/`, `offline/`, `frontend/`, `examples/`, DesignSpec
execution, the offline workflow, a PySide6 design frontend, V-IPM workflow,
and `inspect-jmdl` are absent.

## M1 scope boundary

M1 does not create Geometry, update Design Table parameters, execute a Study,
run a solver or Scheduler, delete results, or promote a capability. A real
JMAG Designer 25.1 smoke remains pending explicit source, target, study, and
launch/save authorization.
