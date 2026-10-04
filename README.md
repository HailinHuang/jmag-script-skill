# JMAG Script Skill

`jmag-script-skill` is a Python library and repository-local tooling for JMAG
Designer 25.1. The Python library is the only source of functional truth.
Codex and ChatGPT are its primary consumers; the CLI and GUI tools are calling
surfaces, not independent capability sources.

Current work focuses on protected project management, Geometry helpers, and
explicit parameter and case automation.

## Install on another Windows computer

Install Git and Python 3.11 or later (Python 3.12 is recommended). Clone the
whole repository: `SKILL.md` depends on the Python source, catalogs, and Help
index beside it. The core CLI has no third-party runtime dependencies.

Run in PowerShell, using an empty destination:

```powershell
$skillPath = Join-Path $env:USERPROFILE ".codex\skills\jmag-script"
git clone https://github.com/HailinHuang/jmag-script-skill.git $skillPath
Set-Location $skillPath
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\jmag-skill.exe --help
.\.venv\Scripts\jmag-skill.exe search "set equation parameter"
```

Use an editable installation (`-e .`): the CLI reads repository-relative
catalogs and tests. A regular wheel installation does not include those
repository resources. Although the package metadata currently permits Python
3.10, the library uses `typing.Self`, which requires Python 3.11 or later.

The default Codex skill directory is shown above. If `CODEX_HOME` is configured,
use its `skills\jmag-script` directory instead. The skill is available on the
next turn; invoke it with `$jmag-script`. If it is not discovered, start a new
chat after installation. Tell the agent the full CLI path above, or put
`.venv\Scripts` on the PATH inherited by Codex so `jmag-skill` resolves.

An empty `functions` list from `search` is expected while the catalog has no
`stable` entries. Installation does not promote verified candidates.

### Local JMAG installation and Help

Live automation requires an installed, licensed JMAG Designer 25.1 and its
Python API runtime. Installing the skill does not install or license JMAG.
Offline CLI discovery and tests do not start JMAG.

For JMAG installed at `C:\Program Files\JMAG-Designer25.1`, the existing
`.\jmag-skill.cmd` launcher uses JMAG's bundled Python 3.12. The default Help
location is `C:\Program Files\JMAG-Designer25.1\Help\en\Script`; the actual
Help HTML must be present on the other computer. The repository contains its
metadata index.

If the Help directory is elsewhere, pass its local path explicitly:

```powershell
.\.venv\Scripts\jmag-skill.exe build-index --help-root "D:\JMAG-Designer25.1\Help\en\Script"
.\.venv\Scripts\jmag-skill.exe help "Study RunAllCases" --max-topics 3 --help-root "D:\JMAG-Designer25.1\Help\en\Script"
```

`build-index` rewrites `references/help-index.jsonl` from that local Help tree.
The checked-in `.cmd` launcher has a fixed installation path; use the installed
CLI for offline work when JMAG is installed elsewhere. For live scripts, use
the local JMAG Python runtime and configure that script's JMAG installation
path explicitly.

### Update an installed clone

Keep machine-specific projects and run output outside the skill clone. From
the clone, run:

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\jmag-skill.exe verify
```

If Git reports local changes, review them before updating; a locally rebuilt
Help index may need to be preserved separately. `verify` runs the offline
tests. Live JMAG smoke verification remains a separate, explicit operation.

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
