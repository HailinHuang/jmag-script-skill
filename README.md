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

The seed APIs are currently `verified`, not `stable`: fake-object tests, installed wrapper signatures, and application lifecycle smoke have passed, but a controlled real JMAG study fixture has not. They are intentionally excluded from default search and project sync until that evidence exists.

The current `promote` command performs the explicit approval transition only. Stable publication remains fail-closed until the planned transactional verifier can run RED/GREEN evidence, real JMAG study smoke, catalog/version update, commit, and REM as one operation.

Project synchronization creates a lock file and copies only requested stable modules and dependencies. It does not initialize Git in the target project.

Use `jmag-skill rollback <project>` to restore the most recent function-lock snapshot created before an update.
