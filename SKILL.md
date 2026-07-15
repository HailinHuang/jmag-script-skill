---
name: jmag-script
description: Use for writing, analyzing, debugging, or planning Python automation that controls JMAG Designer, and for evaluating whether proven JMAG project code should become reusable capability.
---

# JMAG Script

Start with `jmag-skill search` and load only metadata plus the selected stable module. If no stable function matches, run `jmag-skill help`; retrieve at most three anchored Help topics and verify every JMAG method before proposing executable code. Keep case numbering explicit and keep paths, study names, limits, response names, and machine constants in project configuration.

Implement in the project first. Run static tests, fake-object tests, and—when JMAG behavior matters—a JMAG 25.1 smoke test. Never delete results, run studies, load projects, or change central capability unless the request authorizes it.

After a successful task, use `jmag-skill inspect` only to create an observed candidate. Report reuse value, project leakage, Help sources, and evidence; never promote automatically. Promotion requires verified evidence and explicit user approval, then RED–GREEN–REFACTOR, fresh unit/integration/JMAG/behavior verification, catalog and version updates, and an isolated commit. Only stable functions appear in default search.

Use project `.claude/memory` through REM for events, failures, versions, and unpromoted candidates. REM is evidence, never the source of API truth or function bodies.
