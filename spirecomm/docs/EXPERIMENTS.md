# Experiment Log

## Experimental conditions

The project compares three conditions while keeping the gameplay environment and controller capabilities as constant as practical.

### Condition A — Baseline

- No cross-run learning.
- Every LLM decision is made from the current state only.
- No previous-run reflection or memory is available.

### Condition B — Pure self-reflection

- After each completed run, the agent generates at most three reusable lessons using `reflection-v0.2`.
- Lessons are stored automatically without human semantic filtering.
- Future decisions retrieve at most three lessons from the matching decision category.
- If no relevant memory exists, the actor prompt is left unchanged.

### Condition C — Human feedback

- Uses the same actor, reflection timing, lesson schema, memory capacity, and retrieval policy as Condition B.
- The intended experimental difference is that a human reviews/corrects the LLM's reflection before it is stored.

The comparative goal is to identify where pure self-reflection fails and how human feedback specifically helps.

---

## Batch S0 — v0.2.1 integration/smoke runs

**Purpose:** determine whether the expanded controller could repeatedly play real runs without major interface blockers before freezing a baseline agent.

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

**Problems discovered**

- MAP choices could be confused with numeric `x` coordinates.
- Key ownership telemetry was absent in the installed CommunicationMod state despite successful key actions.

These issues were fixed before the final baseline freeze.

---

## Final Condition A baseline — `baseline-v1.0.5`

**Status:** Complete

**Dataset:** `spirecomm/runs/baseline_v1_30runs_final/`

**Configuration**

- Agent: `baseline-v1.0.5`
- Model: `gpt-5.6-luna`
- Character: Ironclad
- Ascension: 0
- Completed runs: 30
- Session size: 5 completed runs
- Cross-run learning: disabled

### Primary results

| Metric | Result |
|---|---:|
| Wins | 0 / 30 |
| Mean floor | 23.37 |
| Median floor | 24 |
| Minimum floor | 7 |
| Best floor | 50 |
| Mean score | 200.43 |
| Median score | 204.5 |
| Best score | 684 |
| Reached Act 2 | 20 / 30 (66.7%) |
| Reached Act 3 | 1 / 30 (3.3%) |

### Stage progression

- 3 runs died before the Act 1 boss.
- 7 died to the Act 1 boss.
- 20 cleared Act 1 and entered Act 2.
- 14 of those died before the Act 2 boss.
- 5 died to the Act 2 boss.
- 1 cleared Act 2 and later died to the Act 3 boss.

### LLM/API usage

- LLM calls: 6,798
- Input tokens: 4,646,344
- Output tokens: 3,017,176
- Combined tokens: 7,663,520
- Mean latency: 6.85 s
- Median latency: 6.54 s
- Approximate p95 latency: 14.34 s
- Approximate total gameplay time: 16.17 h
- Average run duration: 32.34 min

### Decision counts

| Decision type | Count |
|---|---:|
| COMBAT | 5,190 |
| CARD_REWARD | 428 |
| MAP | 282 |
| GRID | 227 |
| HAND_SELECT | 197 |
| EVENT | 152 |
| SHOP | 122 |
| REST | 100 |

### Main behavioural findings

The dominant performance bottleneck was mid-Act-2 attrition and survival/risk management.

Repeated patterns included:

- low-HP smithing before dangerous fights;
- limited card skipping and relatively large final decks;
- resource and potion timing issues;
- repeated deaths to Act 2 elites/hallway fights;
- difficulty balancing short-term offense against long-term survivability.

Card rewards were skipped only 12 times out of 428 (2.8%), making deck growth/skip discipline an important candidate behaviour for later learning analysis.

### Infrastructure caveats

- One decoder fallback occurred in a deterministic Sapphire Key decision.
- Four CommunicationMod errors occurred across two completed runs and auto-recovered.
- Zero API failures occurred inside the final 30 completed baseline runs.
- One interrupted infrastructure run before completed Run 15 was explicitly excluded and did not count toward the 30-run baseline.

**Decision:** freeze this dataset as Condition A.

---

## Reflection-v0.2 offline validation

Before enabling live learning, the reflector was tested on held-out baseline trajectories.

The reflector was required to:

- output at most three lessons;
- verify claims against trajectory evidence;
- cite 1–3 evidence points per lesson;
- check card counts against the final build when needed;
- distinguish permanent deck additions from generated combat cards;
- avoid unsupported map-topology claims;
- reason sequentially about combat legality and temporal state;
- lower confidence when counterfactual evidence is incomplete.

Validation runs showed a mixture of useful, plausible-but-imperfect, and occasionally wrong lessons. These imperfections were intentionally not manually corrected for Condition B because autonomous reflection quality is part of the research question.

---

## Memory retrieval validation

A prototype JSONL memory bank was used to validate retrieval before enabling online learning.

**Frozen retrieval policy**

- exact decision category only;
- newest matching lessons first;
- maximum three lessons;
- no human semantic filtering;
- no `GENERAL` fallback into unrelated specialist categories;
- empty retrieval leaves the original actor prompt unchanged.

This design was chosen for interpretability rather than retrieval sophistication.

---

## Online self-reflection smoke test

**Status:** Complete

A two-run technical smoke test validated the complete learning loop.

Run 1 began with empty memory. After `RUN_END`, the post-run reflector generated two lessons and appended them to memory. Run 2 then retrieved only those prior-run lessons in matching categories. Run 2 completed and generated three additional lessons.

The smoke test verified:

- memory starts empty;
- baseline-equivalent prompts are preserved when retrieval is empty;
- reflection occurs once after each completed run;
- lessons are appended only after `RUN_END`;
- later runs can retrieve prior-run memories without restarting the process;
- memory retrieval IDs/categories match the requested decision category;
- crash recovery retries missing post-run reflection before starting a later run;
- reflection failure pauses the experiment rather than silently continuing with stale memory.

These smoke runs are infrastructure validation only and are not part of the Condition B experimental dataset.

---

## Condition B — 30-run pure self-reflection experiment

**Status:** Ready for data collection

**Planned configuration**

- Agent: `self-reflection-condition-b-v1.0.0`
- Model: `gpt-5.6-luna`
- Character: Ironclad
- Ascension: 0
- Completed runs: 30
- Session size: 5 completed runs
- Reflection: `reflection-v0.2`
- Memory starts empty at Run 1
- Reflection frequency: once after every completed run
- Lessons stored per run: at most 3
- Retrieval: exact category, newest first, max 3
- Human filtering/correction: none

### Evaluation plan

Compare Condition B with the frozen Condition A baseline using:

- win rate;
- mean/median/best floor;
- Act clear rates;
- score distribution;
- death distribution;
- low-HP campfire decisions;
- card skip/deck-size behaviour;
- potion/resource usage;
- repeated failure patterns;
- LLM calls, tokens, and latency;
- lesson generation/retrieval frequency;
- whether repeated baseline mistakes disappear, persist, or are replaced by new mistakes.

A key qualitative analysis will identify cases where the agent generated a useful lesson but failed to apply it, generated an incorrect lesson, or never identified the real causal mistake.

---

## Condition C — Human feedback experiment

**Status:** Planned after Condition B

Condition C will keep the same actor/controller, reflection timing, lesson schema, memory capacity, retrieval policy, and run count as Condition B where practical.

The intended difference is post-run human curation of the LLM reflection. Human interventions will be categorized, for example, as:

- accept;
- wrong cause / credit assignment correction;
- missed insight addition;
- vague-to-specific correction;
- false lesson rejection.

The final comparison will focus on **which autonomous reflection failures are corrected by human input and whether those corrections change later gameplay behaviour**.
