# Frozen Experiment Archives

This directory contains versioned experimental datasets and diagnostic archives for the Slay the Spire LLM FYP.

## Final datasets

- `baseline_v1_30runs_final/` — Condition A baseline, 30 valid runs.
- `condition_b_self_reflection_30runs_final/` — Condition B, 30 valid self-reflection runs using the original newest-3 memory design.
- `condition_c_human_feedback_30_runs/` — Condition C1, 30 human-reviewed runs using the original memory design.
- `B2_v1_1_1_15runs_final/` — **final B2 autonomous control**, 15 matched runs using cumulative-playbook-v2 and the corrected card-reward skip guard.

## Diagnostic / non-final archives

- `deprecated_controllers/` — superseded controller snapshots retained for provenance; these are not active experiment controllers.

- `B2_v1_1_0_invalidated_card_skip_bug/` — completed B2 batch invalidated because skipped permanent card rewards were reopened.
- `C2_v1_1_0_interrupted_card_skip_bug/` — interrupted C2 attempt from before the same controller bug was fixed.
- `C2_B2_smoke_v0.1runs/` — smoke and development artifacts for the B2/C2 follow-up.

## Source-of-truth rule

Final analyses should use only datasets explicitly marked final. Diagnostic and smoke directories are retained for provenance and debugging and must not be mixed into final performance comparisons.

The current official human-taught condition is C2 v1.2.0 using authoritative verbatim human teaching. When its 15-run batch is accepted, freeze it in a new versioned directory alongside the final B2 control.
