# Experiment Log

## Batch S0 — v0.2.1 integration/smoke runs

**Purpose:** Determine whether the expanded controller can repeatedly play real runs without interface blockers before freezing a baseline agent.

**Configuration**
- Agent: `v0.2.1`
- Character: Ironclad
- Ascension: 0
- Cross-run reflection/memory: disabled
- Structured source: `run_events.jsonl`

**Completed runs analysed:** 5

| Run | Furthest floor | Result / endpoint |
|---|---:|---|
| 1 | 16 | Loss — Hexaghost |
| 2 | 16 | Loss — Slime Boss |
| 3 | 33 | Loss — Collector |
| 4 | 16 | Loss — The Guardian |
| 5 | 30 | Loss — Act 2 combat |

**Aggregate**
- Average floor: 22.2
- Act 1 clears: 2/5 (40%)
- Wins: 0/5
- Logged `UNHANDLED_STATE`: 0
- Logged controller `ERROR`: 0
- Boss reward selection: live verified
- Combat potion usage/replacement: live verified
- Sapphire Key trade-off: live exercised

**Problems discovered**
- Six MAP LLM calls fell back because numeric outputs matched map `x` coordinates rather than valid zero-based action indexes.
- Key ownership telemetry was absent (`keys = null`, `final_keys = {}`) despite successful Sapphire Key choices.

**Decision:** do not call this the final baseline. Fix only the map decoder and key telemetry, then run another smoke batch.

## Batch S1 — v0.2.2 baseline-candidate smoke runs

**Status:** Pending

**Target:** 5 completed runs.

**Acceptance checks**
- `UNHANDLED_STATE = 0`
- controller `ERROR = 0`
- no true MAP fallbacks caused by index/coordinate ambiguity
- key ownership appears correctly in structured events after key acquisition
- run end -> new run remains automatic

If these checks pass, freeze the controller/prompt strategy as **Baseline Agent v1.0** before collecting the larger baseline dataset.

## Planned baseline experiment

After the baseline is frozen, collect enough independent runs to establish reliable performance metrics before adding cross-run learning/reflection.

Suggested reported metrics:
- win rate
- average/median floor reached
- Act 1/2/3 clear rates
- boss clear/death distribution
- LLM calls per run
- token usage per run
- latency per decision/run
- true invalid/fallback action rate
- potion use patterns
- controller/interface failure rate

## Planned learning experiment

Compare the frozen baseline agent against a later agent that retrieves lessons/reflections from previous runs. Keep controller capabilities and evaluation metrics as constant as practical so improvements can be attributed to the learning mechanism rather than interface changes.
