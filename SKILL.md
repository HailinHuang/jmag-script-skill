---
name: jmag-script
description: Use for writing, analyzing, debugging, or planning Python automation that controls JMAG Designer, and for evaluating whether proven JMAG project code should become reusable capability.
---

# JMAG Script

The Python library is the functional source of truth. Start with
`jmag-skill search` and load only metadata plus the selected stable module. If
no stable function matches, run `jmag-skill help`; retrieve at most three
anchored Help topics and verify every JMAG method before proposing executable
code. Keep case numbering explicit and keep paths, study names, limits,
response names, and machine constants in project configuration.

`references/function-catalog.json` governs Agent capability status only.
Public exports do not imply `verified` or `stable`; this commit has no stable
capability. Executor, offline, PySide6 design frontend, and V-IPM workflows
are planned, not present. The target runtime is JMAG Designer 25.1 only.

Implement in the project first. Run static tests, fake-object tests, and, when
JMAG behavior matters, a JMAG 25.1 smoke test. Never delete results, run
studies, load projects, or change central capability unless the request
authorizes it.

For projects, use protected-copy functions. Never modify the source directly.
Never run Studies or delete results. Copy `.jproj` plus `.jfiles` on
the filesystem, never `SaveAs`; declare ownership explicitly, never from a
global application. `open_jmag_fast` is legacy, not an M1 entry point.

After a successful task, use `jmag-skill inspect` only to create an observed
candidate. Report reuse value, project leakage, Help sources, and evidence;
never promote automatically. Promotion requires verified evidence and explicit
user approval, then RED-GREEN-REFACTOR and fresh verification. Only stable
functions appear in default search.

Use project `.claude/memory` through REM for events and evidence boundaries;
REM is never the source of API truth or function bodies.
