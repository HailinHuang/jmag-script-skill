# JMAG Script Skill

This repository provides bounded JMAG Help retrieval, a tested Python capability library, candidate lifecycle enforcement, and locked project synchronization for JMAG Designer 25.1.

## Quick start

```powershell
.\jmag-skill.cmd build-index
.\jmag-skill.cmd search "set equation parameter"
.\jmag-skill.cmd help "Study RunAllCases" --max-topics 3
.\jmag-skill.cmd verify
```

The checked-in launcher uses the JMAG 25.1 bundled Python, so no global Python installation is required.

`run_cases` follows the approved initial contract and defaults to `clear_results=True`; pass `clear_results=False` when existing results must be preserved. Setters never delete results implicitly.

Candidate inspection never changes the stable library. Promotion requires `verified` state and `--approved`; a separate fresh verification must pass before `stable` publication.

Project synchronization creates a lock file and copies only requested stable modules and dependencies. It does not initialize Git in the target project.

Use `jmag-skill rollback <project>` to restore the most recent function-lock snapshot created before an update.
