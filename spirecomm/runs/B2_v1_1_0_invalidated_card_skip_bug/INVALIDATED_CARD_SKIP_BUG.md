# B2 v1.1.0 — INVALIDATED FOR FINAL COMPARISON

This directory contains the completed B2 v1.1.0 cumulative-memory batch.

It is retained for debugging and provenance, but it must **not** be used as the final B2 control dataset.

## Reason

The v1.1.0 controller reopened permanent card rewards after the LLM selected Skip because CommunicationMod continued exposing the skipped card reward on the parent `COMBAT_REWARD` list.

Retrospective audit found:

- 92 Skip decisions across 19 affected permanent card-reward instances;
- 9 of 15 completed runs affected;
- maximum 29 repeated skips at one reward;
- every affected reward eventually resolved by taking a card or Singing Bowl.

Because this changed permanent deck construction, downstream trajectories and learned memory were also affected.

## Resolution

`card-reward-skip-guard-v1` was added in v1.1.1. It tracks skipped permanent card rewards within the current reward flow, prevents the same declined reward from reopening, and still allows later distinct card rewards.

B2 was restarted from empty memory using `test_connection_b2_v1_1_1.py`.

The corrected final control is:

```text
../B2_v1_1_1_15runs_final/
```

The final C2 treatment is:

```text
../C2_v1_2_1_15runs_final/
```

Only those explicitly versioned final datasets are used in the final matched B2/C2 comparison.
