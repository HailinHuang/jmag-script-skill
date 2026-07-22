# Milestone 0 Repository Truth

Base commit: `03bbbe73f112d56061604b51de039f0657826dd7`
Runtime: JMAG Designer 25.1

## Present in this tree

- Discoverable Python packages: `jmag_functions` and `jmag_skill`.
- CLI commands: `search`, `help`, `inspect`, `promote`, `sync`, `rollback`,
  `verify`, and `build-index`.
- Runtime frontend: `jmag_user_py/jmag_runtime_frontend.py`.
- Geometry helpers in `src/jmag_functions/geometry_templates.py` and
  `geometry_template_ui.py`. They are Python APIs, not a standalone stable
  Agent capability.
- Capability catalog: six `verified` entries and zero `stable` entries.

Public Python exports are a library surface; they do not infer catalog status.

## Planned—not present in this tree

`src/jmag_skill/executor/`, `offline/`, `frontend/`, `examples/`, DesignSpec
execution, the offline workflow, a PySide6 design frontend, V-IPM workflow,
and `inspect-jmdl` are absent.

## M0 verification status

M0 aligns documentation, metadata, and offline tests to these boundaries. It
does not run a JMAG Study, solver, Scheduler, or real smoke test.
