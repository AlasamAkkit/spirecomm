# Historical one-time utilities (not used by the A10 agent)

This directory groups completed-phase, **inactive** scripts to keep the
`spirecomm/` root readable. They are not part of the Run-39+ execution path.
They have been preserved for auditability, not deleted.

| Scripts | Historical purpose |
|---|---|
| `test_connection_c2_finalize_run28.py`, `run32.py`–`run36.py` | Resume a specific already-ended run's review while preventing the next run from starting |
| `freeze_c2_run28_checkpoint.py`, `run32.py`–`run35.py` | Create historical longitudinal checkpoints after architecture interventions |
| `freeze_c2_run36_stable_baseline.py` | Preserve the pre-v1.4 fixed-controller checkpoint |
| `activate_c2_stable.py` | Historical Run-36 → Run-37 activation |
| `prepare_c2_continual.py` | Historical Run-15 → Run-16 continual experiment setup |

### Important

- **Do not run these helpers against the current A10 experiment.** Their
  historical hard-coded run bounds and assumptions are obsolete.
- The archived helpers still use paths under `spirecomm/` and `reflection/`.
  Their root-path constants have been updated for this nested directory.
  Freeze helpers referencing finalize wrappers now point here as well.
- We deliberately did **not** move `test_connection_c2_continual_v1*.py`.
  The current stable controller imports them through fixed file paths. Those
  modules are genuine runtime dependencies despite their historical names.
- For Run 39 onward, use `spirecomm/test_connection.py` as the launcher,
  `reflection/feedback_app.py` for post-run teaching and
  `spirecomm/finalize_pending_review.py` for offline finalization if needed.
- For strict reproduction of the exact original pre-archive working tree,
  consult Git history at the original path. The historical run data and
  original commits remain intact.
