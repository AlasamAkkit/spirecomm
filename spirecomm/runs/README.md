# Experiment and Checkpoint Archives

This directory contains frozen final datasets, continual-phase checkpoints, smoke/development artifacts, and invalidated diagnostic runs for the Slay the Spire LLM FYP.

## Canonical final controlled datasets

- `baseline_v1_30runs_final/` — Condition A baseline, 30 valid no-memory runs.
- `condition_b_self_reflection_30runs_final/` — Condition B, 30 autonomous self-reflection runs using newest-first exact-category top-3 retrieval.
- `condition_c_human_feedback_30_runs/` — Condition C1, 30 human-reviewed runs using the same original retrieval design.
- `B2_v1_1_1_15runs_final/` — **canonical final B2 autonomous cumulative-memory control**.
- `C2_v1_2_1_15runs_final/` — **canonical final C2 authoritative human-taught treatment**.

For the matched B2/C2 comparison, use only:

```text
B2_v1_1_1_15runs_final/
C2_v1_2_1_15runs_final/
```

Headline matched results:

| Metric | B2 v1.1.1 | C2 v1.2.1 |
|---|---:|---:|
| Runs | 15 | 15 |
| Wins | 0 | 0 |
| Mean floor | 18.73 | **27.33** |
| Median floor | 16 | **23** |
| Best floor | 29 | **50** |
| Mean score | 144.60 | **251.47** |
| Best score | 251 | **629** |
| Act 2+ | 6/15 | **13/15** |
| Act 3 | 0/15 | **2/15** |

## Continual-C2 checkpoints

These are longitudinal research checkpoints, not additional matched-control datasets.

### `C2_continual_v1_0_through_run28/`

Frozen state through Run 28, immediately before the card-prior/turn-planner intervention.

Represents the original continual C2 architecture inherited from the controlled system.

### `C2_continual_through_run32_pre_v1_2/`

Frozen state after Run 32 and before the persistent-planning intervention.

Validated checkpoint:

- completed/reflected runs: 32;
- raw lessons: 46;
- playbook rules: 32;
- feedback rows: 32;
- Run 32 controller: `c2-continual-teaching-v1.1.1-card-prior-turn-planner`.

### `C2_continual_through_run33_pre_v1_2_1/`

Immutable post-Run-33 state before the Run-34 ranking hotfix. Run 33 was LOSS, Act 2 Floor 33, score 292, under v1.2.0 persistent planning.

### `C2_continual_through_run34_pre_v1_3/`

Run 34 played under v1.2.1 applicability/recency focused-memory hotfix (LOSS, Act 2 Floor 22, score 194). Validated checkpoint: **48 raw lessons, 34 playbook rules**. The remaining older-teaching top-k problem motivated all-applicable retrieval.

### `C2_continual_through_run35_pre_v1_3_1/`

Run 35 played under v1.3.0 cumulative policy + independent verifier (LOSS, Act 2 Floor 33, score 273). Validated checkpoint: **49 raw lessons, 35 rules**. Frail effective-Block error motivated v1.3.1.

### `C2_continual_through_run36_pre_stable/` — local baseline snapshot

Created on the user's laptop by `activate_c2_stable.py` as a compressed, integrity-hashed `RUN36_DATA_SNAPSHOT.zip` plus `CHECKPOINT_SUMMARY.json`; **not presumed available on GitHub without a separate commit/push**.

Verified local baseline: **36 completed and reflected runs, 50 raw lessons, 36 playbook rules, 36 feedback records**, before stable v1.4.0 begins at Run 37. The one-time activation passed 10 regression tests.

Archive interpretation: snapshots are historical provenance, not new standalone datasets. Run 37 was reported running; do not write a Run-37 result until final logs exist.


## Invalidated / diagnostic archives

- `B2_v1_1_0_invalidated_card_skip_bug/` — completed B2 batch invalidated because skipped permanent card rewards could reopen.
- `C2_v1_1_0_interrupted_card_skip_bug/` — interrupted C2 attempt from before the permanent-card-reward fix.
- `C2_v1_2_0_invalidated_metadata_scope_bug/` — C2 authoritative-teaching attempt invalidated because Neow teaching lacked `GENERAL` retrieval scope.
- `C2_B2_smoke_v0.1runs/` — cumulative-memory smoke/development artifacts.
- `B2_15runs_final/` — legacy minimal duplicate of the final B2 event log. Prefer the versioned `B2_v1_1_1_15runs_final/` archive because it contains the fuller frozen artifact set.

Smoke, interrupted, and invalidated datasets are retained for provenance only and must not be included in final performance comparisons.

## Controlled vs continual interpretation

The final B2/C2 archives answer the controlled research question:

> Does authoritative human teaching improve progression relative to autonomous self-reflection under the same cumulative-memory design?

The continual checkpoints answer a different exploratory question:

> What limitations emerge as human teaching accumulates, and how does behavior change across explicit controller interventions?

Do not combine these two analyses as if they were one homogeneous experiment.

## Machine-readable source of truth

For a frozen batch, the structured `run_events_*.jsonl` file is the machine-readable source of truth for:

- run starts/ends;
- controller/version metadata;
- decisions and legal actions;
- memory retrievals;
- runtime errors/retries;
- post-run reflection completion.

For the active continual phase, use the live condition-C2 event log plus the reflection/memory artifacts described in `../../reflection/README.md`.

## Related documentation

- `../docs/protocols/B2_C2_FINAL_PROTOCOL.md` — final matched experiment protocol.
- `../docs/protocols/C2_CONTINUAL_TEACHING_PROTOCOL.md` — active continual teaching protocol.
- `../docs/CONTROLLER_HISTORY.md` — controller/version mapping.
- `../docs/CONTINUAL_C2_STATUS.md` — current longitudinal status.
