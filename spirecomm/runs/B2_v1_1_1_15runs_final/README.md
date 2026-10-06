# B2 v1.1.1 — Final 15-Run Autonomous Control

This directory is the canonical frozen archive for the final autonomous B2 control used in the matched B2/C2 comparison.

## Configuration

- agent: `followup-b2-v1.1.1`
- model: `gpt-5.6-luna`
- character: Ironclad
- Ascension: 0
- official seed order: `260925001` through `260925015`
- memory: `cumulative-playbook-v2`
- human review: none
- matched treatment: `../C2_v1_2_1_15runs_final/`

## Final results

| Metric | B2 v1.1.1 |
|---|---:|
| Runs | 15 |
| Wins | 0 |
| Mean floor | 18.73 |
| Median floor | 16 |
| Best floor | 29 |
| Mean score | 144.60 |
| Median score | 112 |
| Best score | 251 |
| Act 2+ | 6/15 |
| Act 3 | 0/15 |
| Raw lessons | 38 |
| Playbook rules | 14 |

Integrity audit:

- 15 starts / 15 completions / 15 completed reflections;
- exact matched seed order;
- 2,924 memory retrievals;
- zero detected current-run/future-run memory leakage;
- complete raw-memory source coverage;
- permanent-card-reward skip guard live-validated;
- one two-card-reward case correctly skipped the first reward and processed the second.

## Why v1.1.1 exists

B2 v1.1.0 was invalidated after discovering that skipped permanent card rewards could reopen while CommunicationMod continued exposing them on the parent reward list.

The corrected v1.1.1 controller added `card-reward-skip-guard-v1` and restarted the experiment from empty memory.

Do not use:

```text
../B2_v1_1_0_invalidated_card_skip_bug/
```

for final analysis.

## Contents

This canonical archive includes the frozen B2 structured event log, raw memory, playbook, per-run reflection outputs, and final controller snapshot.

A legacy directory `../B2_15runs_final/` contains the same final B2 event-log blob but is not the canonical reproducibility archive.

See `../../docs/FINAL_B2_C2_ANALYSIS.md` and `../../FOLLOWUP_B2_C2_FINAL_PROTOCOL.md` for the final comparison and protocol history.
