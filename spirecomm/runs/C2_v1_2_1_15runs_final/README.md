# C2 v1.2.1 — Final 15-Run Matched Treatment

This directory is the frozen Git archive for the final authoritative human-taught C2 condition.

## Configuration

- agent: `followup-c2-v1.2.1`
- model: `gpt-5.6-luna`
- character: Ironclad
- Ascension: 0
- official seed order: `260925001` through `260925015`
- memory: `cumulative-playbook-v2`
- teaching policy: `authoritative-human-teaching-v1`
- matched autonomous control: `../B2_v1_1_1_15runs_final/`

## Final results

| Metric | C2 v1.2.1 |
|---|---:|
| Runs | 15 |
| Wins | 0 |
| Mean floor | 27.33 |
| Median floor | 23 |
| Best floor | 50 |
| Mean score | 251.47 |
| Median score | 197 |
| Best score | 629 |
| Act 2+ | 13/15 |
| Act 3 | 2/15 |
| Raw lessons | 25 |
| Playbook rules | 17 |

Human-review outcomes:

- 10 `HUMAN_TEACHING`
- 5 `APPROVE_INITIAL`

Integrity audit:

- 15 starts / 15 completions / 15 completed reflections;
- exact matched seed order;
- 3,705 memory retrievals;
- zero detected current-run/future-run memory leakage;
- complete raw-memory source coverage;
- authoritative human teaching preserved verbatim.

## Matched B2 comparison

B2 v1.1.1 had mean floor 18.73 and mean score 144.60.

C2:

- reached a higher floor on 11/15 matched seeds;
- had a mean paired gain of +8.60 floors;
- achieved a higher score on 10/15 matched seeds;
- had a mean paired gain of +106.87 score;
- reached Act 3 twice, while B2 did not reach Act 3.

Neither condition achieved a win.

## Files committed here

At the time this archive was frozen, Git contains:

- `run_events_c2.jsonl` — official structured event log;
- `test_connection_c2_v1_2_1.py` — official final controller snapshot;
- `test_connection_c2_v1_2_1_scope_smoke.py` — dedicated retrieval-scope smoke controller used before final collection.

## Important artifact note

The following official C2 files were Git-ignored during collection and are therefore not currently committed in this directory:

- raw C2 memory JSONL;
- final C2 playbook JSON;
- human feedback bank;
- per-run reflection/output files;
- ordinary debug/message logs.

They were separately validated during the final integrity audit. Preserve them externally if full reflection-level reproducibility is required.

## Runtime caveats

- One transient API HTTP 500 recovered successfully on retry without substituting a gameplay action.
- Two LLM calls returned out-of-range indexes and used the frozen deterministic index-parser fallback.
- The affected runs were retained rather than selectively rerun.

## Do not confuse with invalidated attempts

Do not use:

- `../C2_v1_1_0_interrupted_card_skip_bug/`
- `../C2_v1_2_0_invalidated_metadata_scope_bug/`

for final performance analysis.

See `../../docs/FINAL_B2_C2_ANALYSIS.md` and `../../FOLLOWUP_B2_C2_FINAL_PROTOCOL.md` for the final comparison and protocol history.
