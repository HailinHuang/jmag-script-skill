# Verification record

## 2026-07-15

- Behavior/unit/integration: 17 tests passed, 1 real-JMAG test skipped under standard Python after independent-review fixes.
- Real JMAG: `JMAG_REAL_SMOKE=1` under the bundled Python passed 1 test in 13.855 s.
- JMAG process: hidden Designer created with `--no-splash -g` and closed through `Application.Quit()`.
- Help index: 6,317 anchored method entries; retrieval returns at most three excerpts.
- Plugin: personal Superpowers 6.1.1 compatibility build validated; only one Superpowers provider enabled.
- Known external warning: JMAG emitted a Modeller `QProcess` shutdown warning after the passing smoke test. Pre-existing Designer/Modeller processes had older start times and were not touched.
- Independent review demoted all seed APIs from `stable` to `verified` because real study-bound behavior has not yet been exercised.
- Phase 0 interactive brainstorming acceptance and Phase 1 five-run baseline remain open exit conditions; the platform must not be described as fully released.
