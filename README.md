# JMAG Script Skill

`jmag-script-skill` is a Python library and repository-local tooling for JMAG
Designer 25.1. The Python library is the only source of functional truth.
Codex and ChatGPT are its primary consumers; the CLI and GUI tools are calling
surfaces, not independent capability sources.

Milestone 1 provides protected existing-project management only. Geometry,
parameter changes, and case execution are outside this API.

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

## Canonical protected-copy workflow

```python
from pathlib import Path
from jmag_functions import open_protected_project_copy

source = Path(r"C:\models\source.jproj")
target = Path(r"C:\runs\source_m1_copy.jproj")

with open_protected_project_copy(
    source,
    target,
    visible=False,
    study="Main Study",
    manifest_path=target.parent / "m1_manifest.json",
) as session:
    session.save()
```

The source is never saved, overwritten, or deleted. `target` and its sibling
`.jfiles` directory must not exist; the source `.jfiles` directory, when
present, is copied as part of the filesystem-level bundle. Closing does not save by
default. This API supports JMAG Designer 25.1 only and does not create
Geometry, change parameters, or execute cases.
