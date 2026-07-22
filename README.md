# JMAG Script Skill

`jmag-script-skill` is a Python library and repository-local tooling for JMAG
Designer 25.1. The Python library is the only source of functional truth.
Codex and ChatGPT are its primary consumers; the CLI and GUI tools are calling
surfaces, not independent capability sources.

Current work focuses on protected project management, Geometry helpers, and
explicit parameter and case automation.

## CLI

The installed `jmag-skill` CLI exposes exactly these commands:

```text
search  help  inspect  promote  sync  rollback  verify  build-index
```

Use `python -m jmag_skill.cli --help` for command arguments. The dependency-free
runtime frontend is a separate repository-local tool at
`jmag_user_py/jmag_runtime_frontend.py`.

## Planned—not present in this commit

- DesignSpec executor
- offline workflow
- PySide6 design frontend
- V-IPM reference workflow
- `inspect-jmdl`

Those paths and commands must not be treated as executable in this checkout.

## Python library layout

| Area | Location |
| --- | --- |
| JMAG session, results, parameters, and studies | `src/jmag_functions/` |
| Project lifecycle, inventory, exports, Geometry, runtime management | `src/jmag_functions/` |
| CLI, bounded Help retrieval, inspection, promotion, sync | `src/jmag_skill/` |
| Repository-local JMAG scripts | `jmag_user_py/` |

## Capability boundary

Public exports describe the Python API surface. Agent capability lifecycle is
managed separately by [`references/function-catalog.json`](references/function-catalog.json).
A public export is not automatically `verified` or `stable`. The catalog has
six `verified` entries and zero `stable` entries in this commit.

Use only JMAG Designer 25.1 for JMAG-bound work. No model, Study, solver, or
Scheduler execution is implied by the offline documentation or test suite.
