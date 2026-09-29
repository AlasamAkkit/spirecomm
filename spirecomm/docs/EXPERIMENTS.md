# Experiment Log

## Experimental conditions

The project has two experimental phases.

### Initial study

#### Condition A — Baseline

- No cross-run learning.
- Every LLM decision is made from the current state only.
- No previous-run reflection or memory is available.

#### Condition B — Pure self-reflection

- After each completed run, `reflection-v0.2` generates at most three reusable lessons.
- Lessons are stored automatically without human semantic filtering.
- Future decisions retrieve the newest matching lessons, capped at three.
- If no relevant memory exists, the actor prompt is left unchanged.

#### Condition C1 — Human-curated reflection

- Uses the same general reflection/memory design as Condition B.
- A human reviews the LLM reflection before final lessons are stored.
- Human interventions can accept, correct, reject, or add lessons.

### Matched follow-up study

The first study exposed a memory bottleneck: newest-three exact-category retrieval can forget older useful guidance and can hide cross-category lessons. B2/C2 therefore share a stronger cumulative memory mechanism.

#### Condition B2 — Improved self-reflection

- Completed trajectory -> LLM reflection -> final lessons.
- Every final lesson is retained permanently in raw memory.
- The complete raw-memory history is consolidated into a cumulative playbook.
- The actor receives all playbook rules applicable to the current decision category.

#### Condition C2 — Human-guided reflection

- Completed trajectory -> initial LLM reflection.
- A human reviews the trajectory and gives natural-language run-level feedback.
- The LLM revises the reflection using the trajectory, initial reflection, and human feedback.
- Final lessons enter the same cumulative playbook mechanism used by B2.

B2 and C2 use the same official 15 seeds in the same order. The intended treatment difference is the trajectory-level human feedback in C2.

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

## Condition C1 — 30-run human-curated reflection experiment

**Status:** Complete

**Dataset:** `spirecomm/runs/condition_c_human_feedback_30_runs/`

Condition C1 retained the run-level reflection structure from Condition B but inserted human review before final memory storage.

The review process operated on each completed run's compact trajectory and initial `reflection-v0.2` output. The human could accept a lesson, correct its causal/strategic interpretation, reject it, or add a missed lesson.

### Final retained memory

The completed C1 memory contains **73 final human-curated lessons**.

| Category | Lessons |
|---|---:|
| COMBAT | 30 |
| CARD_REWARD | 17 |
| REST | 12 |
| EVENT | 8 |
| SHOP | 4 |
| GENERAL | 1 |
| BOSS_REWARD | 1 |

Among the retained final lessons, provenance records contain:

- 61 `ACCEPT`;
- 11 `CORRECT`;
- 1 `ADD`.

These figures describe the **retained final lessons**. Rejected candidate lessons are not included in the final-memory total.

Observed correction reasons among retained corrected/added lessons include:

- wrong-cause attribution;
- missed insight;
- over-vague guidance;
- long-horizon planning;
- false lesson.

Examples include correcting overly conservative campfire conclusions, rejecting boss-specific hindsight that was unavailable at the earlier decision, qualifying HP-for-gold/curse-for-gold trade-offs using route context, and reinforcing known card/event interactions.

### Interpretation

C1 demonstrated that human review can improve the semantic quality of individual lessons, especially when the initial reflector assigns blame to the wrong earlier decision or overgeneralizes from the terminal fight.

However, C1 still inherited the same memory interface as Condition B:

- one primary category per lesson;
- newest-first retrieval;
- at most three retrieved lessons.

This means the effect of a good correction can be limited by **whether the memory system surfaces that correction later**.

**Decision:** preserve C1 as the completed human-curated dataset and create a matched B2/C2 follow-up with a shared stronger memory mechanism.

---

## B2/C2 follow-up — cumulative memory experiment

### Motivation

Condition B showed repeated lesson regeneration and a rolling top-3 memory window. C1 showed that human corrections can be semantically useful, but those corrections still pass through the same limited retrieval interface.

The B2/C2 follow-up changes the memory mechanism for both conditions while keeping the human-feedback treatment isolated.

### Shared memory mechanism

Every final lesson is appended permanently to a raw JSONL bank.

A cumulative playbook consolidates the entire history. Each rule stores:

- `when`;
- `guidance`;
- `rationale`;
- confidence;
- `source_memory_ids`;
- one primary category;
- cross-category `applies_to` scopes.

The validator requires every raw lesson ID to remain represented by at least one playbook rule. A playbook update that drops source coverage is rejected.

During gameplay, the actor receives every playbook rule whose `applies_to` includes the current decision category, including GENERAL rules. There is no newest-three truncation.

### C2 smoke v0.1

**Status:** Complete — 2 runs

**Archived controller/data:** `spirecomm/runs/C2_B2_smoke_v0.1runs/` plus C2 smoke reflection artifacts.

The smoke test validated:

- trajectory generation;
- initial LLM reflection;
- browser-based human trajectory feedback;
- revised final reflection;
- final lesson storage;
- cumulative playbook update;
- Run 2 retrieval of Run-1 knowledge without future-run leakage.

### Smoke-v0.1 finding

Run-level human feedback contained advice spanning several decision types. During consolidation, some of that advice was assigned to a single primary category.

Under playbook v1 retrieval, a rule stored under EVENT was only retrieved for EVENT/GENERAL contexts even if part of its guidance also mattered to CARD_REWARD decisions.

This exposed a **cross-category applicability problem** rather than a failure of the human feedback itself.

### B2/C2 v1.1

**Status:** C2 and B2 smoke v0.2 complete; ready for official matched collection.

The cumulative playbook was upgraded to `cumulative-playbook-v2`.

Each rule now has an `applies_to` list. Retrieval scans the complete playbook and returns all rules applicable to the current decision.

This allows, for example, a lesson whose primary provenance is EVENT to also be injected during CARD_REWARD decisions when its guidance concerns deck selectivity.

Official controller files:

- `spirecomm/test_connection_b2_v1_1_0.py`
- `spirecomm/test_connection_c2_v1_1_0.py`

Smoke controller files:

- `spirecomm/test_connection_b2_smoke_v0_2.py`
- `spirecomm/test_connection_c2_smoke_v0_2.py`

### C2 smoke v0.2 results

**Status:** Complete — 2 valid runs.

Run outcomes:

| Run | Result | Act | Floor | Score |
|---|---|---:|---:|---:|
| 1 | Loss | 2 | 25 | 236 |
| 2 | Loss | 3 | 38 | 454 |

Learning-system validation:

- Run 1 retrieved no playbook rules.
- Run 1 final reflection stored three lessons: EVENT, REST, and COMBAT.
- Run 2 retrieved only Run-1 source memory IDs.
- Run 2 contained no current/future-run memory leakage.
- The final raw-memory bank contained six lessons.
- The final playbook contained six rules and reported `playbook_version = cumulative-playbook-v2` with `updated_through_run = 2`.
- All six raw-memory IDs were represented in playbook `source_memory_ids`.
- Cross-category retrieval was observed during Run 2: the REST-primary rule `pb_rest_01` was retrieved for MAP decisions through `applies_to = [REST, MAP]`.

Human feedback also demonstrably changed the final reflection. For Run 1, the initial reflection blamed smithing at 39/56 HP as the main actionable mistake; human feedback redirected the final reflection toward the earlier Bite/max-HP trade and made the rest-site lesson conditional instead of automatically preferring Rest.

### Smoke-v0.2 controller timing finding

Two `COMMUNICATIONMOD_ERROR` events occurred during Run 2 after Smoke Bomb ended an elite combat. A stale command-ready combat snapshot caused an extra tactical `PLAY` decision after the game had already begun transitioning to `COMBAT_REWARD`.

The run recovered and the learning pipeline completed normally. Because the issue is an interface-transition artifact rather than an LLM reasoning failure, a bounded Smoke Bomb transition guard was added to all four current B2/C2 controllers before further data collection.

The C2 memory-system smoke criteria are considered satisfied. B2 smoke v0.2 is the remaining validation step before official collection.

### B2 smoke v0.2 results

**Status:** Complete — 2 valid runs.

Run outcomes:

| Run | Result | Act | Floor | Score |
|---|---|---:|---:|---:|
| 1 | Loss | 2 | 33 | 302 |
| 2 | Loss | 1 | 16 | 104 |

Learning-system validation:

- Run 1 used no learned memory and produced three self-reflection lessons.
- Run 1's three raw lessons were consolidated into five playbook rules.
- Run 2 retrieved only Run-1 source memory IDs.
- No current-run or future-run lesson was retrieved during Run 2.
- Run 2 added three new raw lessons, producing six raw lessons total.
- The final cumulative playbook contained seven rules and reported `updated_through_run = 2`.
- Every raw memory ID remained represented by at least one playbook rule.
- Cross-category retrieval was exercised live. For example, MAP decisions retrieved EVENT/MAP/REST rules sourced from Run 1, while COMBAT decisions retrieved COMBAT/EVENT/MAP/REST rules.
- No `COMMUNICATIONMOD_ERROR`, Python `ERROR`, watchdog, or no-command recovery events occurred.

The Smoke Bomb transition guard was also exercised directly in Run 2. Five transient stale-combat snapshots were handled with `WAIT 30`, after which `SMOKE_BOMB_TRANSITION_COMPLETE` recorded the expected transition to `COMBAT_REWARD`. No invalid post-combat `PLAY` was issued.

B2 smoke v0.2 therefore satisfies the intended v1.1 smoke criteria. Together with the completed C2 smoke v0.2, the matched v1.1 pair is ready to freeze for official data collection.

### Official matched configuration

| Property | B2 | C2 |
|---|---|---|
| Model | `gpt-5.6-luna` | `gpt-5.6-luna` |
| Character | Ironclad | Ironclad |
| Ascension | 0 | 0 |
| Valid run target | 15 | 15 |
| Session checkpoint | 5 runs | 5 runs |
| Seed order | `260925001` … `260925015` | same |
| Raw lesson memory | cumulative | cumulative |
| Playbook | v2 | v2 |
| Cross-category `applies_to` | yes | yes |
| Human trajectory feedback | no | yes |

The B2 and C2 v1.1 gameplay controllers are intentionally the same apart from condition identity, output paths, and human-feedback flow.

### Smoke v0.2 protocol

Do not begin official matched data collection until smoke v0.2 has been verified.

C2 smoke:

1. clear only the `*_smoke_v02` artifacts;
2. activate `test_connection_c2_smoke_v0_2.py` as `test_connection.py`;
3. run `feedback_app.py` against `reflection/condition_c2_outputs_smoke_v02`;
4. complete both matched smoke seeds;
5. verify the final playbook uses `playbook_version = cumulative-playbook-v2`;
6. verify at least one cross-category rule can be retrieved in every category listed in its `applies_to`;
7. verify Run 2 never retrieves knowledge produced by Run 2 itself.

B2 smoke:

1. clear only the B2 `*_smoke_v02` artifacts;
2. activate `test_connection_b2_smoke_v0_2.py`;
3. complete both smoke seeds;
4. verify reflection, raw memory, playbook coverage, and retrieval without any human-feedback dependency.

### Planned official analysis

Because the official seeds are matched, report both aggregate and paired results.

Primary outcome measures:

- mean and median floor;
- mean and median score;
- Act 2/Act 3 reach rates;
- wins;
- paired per-seed floor differences;
- paired per-seed score differences.

Behavioural measures:

- card-reward take/skip behaviour;
- low-HP campfire decisions;
- shop/resource decisions;
- key acquisition and route planning;
- combat survival/ordering errors.

Learning-system measures:

- raw lesson count and category distribution;
- cumulative playbook size/category coverage;
- cross-category rule usage;
- memory retrieval coverage over time;
- repeated/merged strategic ideas;
- initial vs final C2 reflection differences;
- human-feedback themes;
- whether human feedback changes credit assignment or long-horizon planning.

The follow-up should be interpreted as a comparison of **self-reflection vs human-guided reflection under the same improved cumulative-memory interface**, not as a direct replacement for the completed B/C1 datasets.
