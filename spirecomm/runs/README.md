# Frozen Experiment Archives

This directory contains versioned final datasets, smoke/development artifacts, and invalidated diagnostic runs for the Slay the Spire LLM FYP.

## Final datasets

- `baseline_v1_30runs_final/` — Condition A baseline, 30 valid no-memory runs.
- `condition_b_self_reflection_30runs_final/` — Condition B, 30 valid autonomous self-reflection runs using newest-first exact-category top-3 retrieval.
- `condition_c_human_feedback_30_runs/` — Condition C1, 30 human-reviewed runs using the same original retrieval design.
- `B2_v1_1_1_15runs_final/` — **canonical final B2 autonomous cumulative-memory control**, 15 matched runs with `cumulative-playbook-v2` and the corrected card-reward skip guard.
- `C2_v1_2_1_15runs_final/` — **final C2 authoritative human-taught treatment**, 15 matched runs using the same cumulative-memory/controller architecture plus authoritative human review.

## Final B2/C2 headline results

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

Paired across the same seeds, C2 reached a higher floor on 11/15 runs and a higher score on 10/15 runs.

## Diagnostic / non-canonical archives

- `deprecated_controllers/` — superseded controller snapshots retained for provenance; not active experiment controllers.
- `B2_15runs_final/` — a minimal legacy duplicate containing the **same final B2 v1.1.1 `run_events_b2.jsonl` blob** as the canonical versioned archive. Use `B2_v1_1_1_15runs_final/` for analysis and reproducibility because it also contains the frozen memory/playbook/controller artifacts.
- `B2_v1_1_0_invalidated_card_skip_bug/` — completed B2 batch invalidated because skipped permanent card rewards were reopened.
- `C2_v1_1_0_interrupted_card_skip_bug/` — interrupted C2 attempt from before the same permanent-card-reward fix.
- `C2_v1_2_0_invalidated_metadata_scope_bug/` — invalidated authoritative-teaching attempt where Run-1 Neow teaching was not retrieved at Run-2 Neow because `GENERAL` was omitted from retrieval scope.
- `C2_B2_smoke_v0.1runs/` — smoke and development artifacts from the cumulative-memory follow-up.

Other smoke outputs may remain elsewhere in the repository for debugging provenance. Smoke/development runs are never part of final performance analyses.

## Source-of-truth rule

Final analyses must use only datasets explicitly marked final. Diagnostic, interrupted, invalidated, and smoke directories must not be mixed into final performance comparisons.

For a frozen dataset, the structured `run_events_*.jsonl` log is the machine-readable source of truth for run starts, outcomes, decisions, memory retrievals, errors, and experiment completion.

## C2 archive note

The committed `C2_v1_2_1_15runs_final/` directory currently contains:

- the official C2 structured event log;
- the official v1.2.1 controller snapshot;
- the v1.2.1 scope-smoke controller snapshot;
- an archive README.

The raw C2 memory/playbook/reflection-output files were Git-ignored during collection and therefore are not currently present in this Git archive. They were separately validated during the final integrity audit:

- 25 raw lessons;
- 17 playbook rules;
- 10 `HUMAN_TEACHING` reviews;
- 5 `APPROVE_INITIAL` reviews;
- complete raw-memory source coverage;
- verbatim preservation of authoritative human teaching;
- zero current/future leakage across 3,705 retrievals.

Preserve those ignored files separately if full reflection-level reproducibility is required.

## Next phase

The matched B2/C2 experiment is complete. Future work should carry forward C2 on fresh training seeds, then freeze the resulting memory/playbook and evaluate it on a separate held-out seed set with learning disabled.
