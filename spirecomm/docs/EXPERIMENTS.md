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
- The intended difference is that a human reviews/corrects the LLM's reflection before it is stored.

The comparative goal is to identify where pure self-reflection fails and how human feedback specifically helps.

---

## Final Condition A baseline — `baseline-v1.0.5`

**Status:** Complete

**Dataset:** `spirecomm/runs/baseline_v1_30runs_final/`

**Configuration**

- Model: `gpt-5.6-luna`
- Character: Ironclad
- Ascension: 0
- Completed runs: 30
- Session size: 5
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

### LLM/API usage

- LLM calls: 6,798
- Input tokens: 4,646,344
- Output tokens: 3,017,176
- Combined tokens: 7,663,520
- Mean latency: 6.85 s
- Median latency: 6.54 s
- Approximate p95 latency: 14.34 s

### Main behavioural findings

The dominant bottleneck was mid-Act-2 attrition and survival/risk management.

Repeated patterns included:

- low-HP smithing before dangerous fights;
- limited card skipping;
- relatively large decks;
- resource/potion timing issues;
- repeated deaths to Act 2 elites and hallway fights.

Permanent card rewards were skipped only 12 times out of 428 decisions (2.8%).

### Infrastructure caveat

One interrupted infrastructure run before completed Run 15 was excluded and did not count toward the 30-run baseline.

**Decision:** freeze this dataset as Condition A.

---

## Reflection-v0.2 offline validation

Before enabling live learning, the reflector was tested on held-out baseline trajectories.

The reflector was required to:

- output at most three lessons;
- verify claims against trajectory evidence;
- cite evidence points;
- distinguish permanent deck additions from generated combat cards;
- avoid unsupported map-topology claims;
- reason sequentially about combat legality and temporal state;
- lower confidence when counterfactual evidence is incomplete.

Validation produced a mixture of useful, plausible-but-imperfect, and occasionally wrong lessons. These imperfections were intentionally not manually corrected for Condition B.

---

## Memory retrieval validation

**Frozen retrieval policy**

- exact decision category only;
- newest matching lessons first;
- maximum three lessons;
- no human semantic filtering;
- no unrelated `GENERAL` fallback;
- empty retrieval leaves the original actor prompt unchanged.

This simple retrieval design was chosen for interpretability.

---

## Online self-reflection smoke test

**Status:** Complete

A two-run technical smoke test validated the complete learning loop.

Run 1 began with empty memory. After `RUN_END`, the reflector generated two lessons and appended them to memory. Run 2 retrieved only prior-run lessons in matching categories and later generated three additional lessons.

These smoke runs were infrastructure validation only and are not part of the Condition B dataset.

---

## Condition B — 30-run pure self-reflection experiment

**Status:** Complete

**Configuration**

- Agent: `self-reflection-condition-b-v1.0.0`
- Model: `gpt-5.6-luna`
- Character: Ironclad
- Ascension: 0
- Completed runs: 30
- Session size: 5
- Reflection: `reflection-v0.2`
- Memory starts empty at completed Run 1
- Reflection frequency: once after every completed run
- Lessons stored per run: at most 3
- Retrieval: exact category, newest first, max 3
- Human filtering/correction: none

### Integrity checks

| Check | Result |
|---|---:|
| RUN_START | 31 |
| Valid RUN_END | 30 |
| POST_RUN_REFLECTION_START | 30 |
| POST_RUN_REFLECTION_COMPLETE | 30 |
| EXPERIMENT_COMPLETE | 1 |
| Stored memory lessons | 85 |
| Malformed event JSON | 0 |
| Malformed memory JSON | 0 |
| Detected future-memory leakage | 0 |

The extra `RUN_START` corresponds to one interrupted physical run caused by a watchdog/CommunicationMod readiness deadlock. It had no `RUN_END`, generated no reflection, and did not enter the 30-run dataset.

### Condition A vs B performance

| Metric | Condition A | Condition B |
|---|---:|---:|
| Runs | 30 | 30 |
| Wins | 0 | 0 |
| Mean floor | 23.37 | **27.23** |
| Median floor | 24 | **28** |
| Best floor | 50 | 50 |
| Mean score | 200.43 | **236.63** |
| Best score | **684** | 535 |
| Reached Act 2 | 20/30 (66.7%) | **22/30 (73.3%)** |
| Reached Act 3 | 1/30 (3.3%) | **3/30 (10.0%)** |

Condition B increased mean floor by about 3.9 floors and mean score by about 18%, but still produced no win.

### Death distribution

Condition B deaths shifted deeper into the run:

- boss deaths: 18
- elite deaths: 5
- hallway deaths: 6
- event-combat death: 1

The increased boss-death count is interpreted together with deeper average progression rather than as a standalone negative result.

### Card-reward behaviour

Condition A:

- 428 permanent card-reward decisions
- 12 skips
- skip rate: 2.8%

Condition B:

- 491 permanent card-reward decisions
- 69 skips
- skip rate: 14.1%

Condition B therefore became substantially more selective about card rewards.

Average final deck size nevertheless increased from about 24.4 to 25.97 cards, which is compatible with the fact that Condition B progressed farther and encountered more rewards.

### Campfire behaviour

Condition A campfire choices were dominated by smithing.

Condition B recorded approximately:

- Rest: 63
- Smith: 50
- Recall: 7
- Lift: 1

At campfires where HP was at or below 40% of maximum, Condition B rested in **27 of 29** cases.

This is a strong behavioural change relative to the baseline's recurring low-HP smithing pattern.

### Memory generation

Condition B produced 85 lessons:

| Category | Lessons |
|---|---:|
| COMBAT | 27 |
| CARD_REWARD | 18 |
| EVENT | 12 |
| REST | 11 |
| SHOP | 5 |
| GENERAL | 5 |
| POTION | 4 |
| MAP | 2 |
| BOSS_REWARD | 1 |

### Memory retrieval

Across the 30 valid Condition B runs:

- gameplay LLM calls: 9,223
- calls with >=1 retrieved memory: 8,542
- calls with no retrieved memory: 681

Retrieval-count distribution:

| Retrieved lessons | LLM calls |
|---:|---:|
| 3 | 7,425 |
| 2 | 630 |
| 1 | 487 |
| 0 | 681 |

All 681 calls with empty retrieval preserved the base prompt length exactly.

No retrieved memory came from the current or a future run.

### Token usage

Condition B actor calls used:

- input tokens: 9,450,345
- output tokens: 3,697,395
- total actor tokens: 13,147,740

Post-run reflection added:

- input tokens: 256,865
- output tokens: 82,151
- reflection total: 339,016

Approximate total Condition B token usage: **13.49 million**.

This is substantially higher than the 7.66 million-token baseline, partly because Condition B survived longer and partly because retrieved lessons enlarged prompts.

### Within-condition progression

Descriptively:

- Runs 1–10 mean floor: 25.2
- Runs 11–20 mean floor: 26.9
- Runs 21–30 mean floor: 29.6

All three Act 3 runs occurred in the second half.

This trend is consistent with accumulated-memory effects but is not treated as causal proof because game-seed difficulty varies between runs.

### Long-horizon key-planning result

Condition B ended with the Sapphire Key in 25/30 runs, showing that the agent learned the explicit local key trade-off.

However:

- 0/30 runs ended with all three keys;
- each of the three Act 3 runs had Ruby + Sapphire but lacked Emerald.

This is an important example of the difference between learning a local explicit rule and solving a long-horizon planning objective.

### Interpretation

Condition B appears strongest at correcting repeated local/medium-horizon behaviours such as:

- low-HP campfire recovery;
- card-reward selectivity;
- immediate combat survival;
- some event/resource-risk choices.

It remains weak at:

- long-horizon planning;
- causal credit assignment;
- strategic lesson consolidation;
- repeated failures whose root cause occurred much earlier than the terminal fight.

The memory bank also showed substantial lesson repetition. New runs often generated another variant of an existing lesson rather than refining a coherent cumulative strategy.

**Decision:** freeze Condition B as the pure self-reflection dataset.

---

## Condition C — Human feedback experiment

**Status:** Next planned experiment

Condition C should preserve the same actor/controller, reflection timing, lesson schema, memory capacity, retrieval policy, and run count as Condition B where practical.

The intended difference is post-run human curation of the LLM reflection.

Suggested intervention labels:

- accept;
- wrong-cause / credit-assignment correction;
- missed-insight addition;
- vague-to-specific correction;
- false-lesson rejection.

The final comparison should focus on which autonomous reflection failures are corrected by human input and whether those corrected lessons change later gameplay behaviour.
