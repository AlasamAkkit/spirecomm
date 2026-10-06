# Experiment Log

## Overview

The project has progressed through two completed experimental phases and is now ready for a final extended-learning/generalization phase.

### Phase I — initial A/B/C1 study

- **A — Baseline:** no cross-run learning.
- **B — Autonomous self-reflection:** post-run LLM lessons with newest-first exact-category retrieval capped at three.
- **C1 — Human-curated reflection:** the same basic memory interface as B, but a human reviews and edits lessons before storage.

### Phase II — matched B2/C2 follow-up

The first study exposed two memory-interface limitations: older lessons could age out of the active top-3 window, and useful advice could be hidden under a single primary category.

B2/C2 therefore share `cumulative-playbook-v2`:

- permanent raw lesson memory;
- cumulative playbook consolidation;
- `source_memory_ids` provenance;
- `applies_to` cross-category retrieval scopes;
- validation requiring every raw lesson ID to remain represented;
- all applicable playbook rules supplied to the actor.

- **B2 — autonomous cumulative-memory control:** completed trajectory -> autonomous reflection -> memory/playbook.
- **C2 — authoritative human-taught treatment:** completed trajectory -> initial reflection -> human review -> approved lessons unchanged OR verbatim human teaching -> same memory/playbook.

Both final conditions used the same 15 seeds in the same order.

---

# Phase I

## Condition A — final baseline

**Status:** COMPLETE

**Dataset:** `spirecomm/runs/baseline_v1_30runs_final/`

**Configuration**

- agent: `baseline-v1.0.5`
- model: `gpt-5.6-luna`
- character: Ironclad
- Ascension: 0
- cross-run memory: disabled
- completed runs: 30

### Results

| Metric | Condition A |
|---|---:|
| Wins | 0/30 |
| Mean floor | 23.37 |
| Median floor | 24 |
| Best floor | 50 |
| Mean score | 200.43 |
| Median score | 204.5 |
| Best score | 684 |
| Reached Act 2 | 20/30 (66.7%) |
| Reached Act 3 | 1/30 (3.3%) |

### Usage

- gameplay LLM calls: 6,798
- input tokens: 4,646,344
- output tokens: 3,017,176
- combined tokens: 7,663,520
- mean latency: 6.85 s

### Main findings

The dominant bottleneck was mid-Act-2 attrition and resource/risk management rather than a recurring controller blocker. Repeated strategic patterns included low-HP smithing, limited card skipping, growing decks, and imperfect potion/resource timing.

Permanent card rewards were skipped only 12/428 times (2.8%).

One infrastructure-interrupted physical run was excluded because it had no valid completion and did not enter the 30-run dataset.

**Decision:** freeze Condition A as the no-memory baseline.

---

## Reflection-v0.2 validation

Before online learning, post-run reflection was tested offline on held-out baseline trajectories.

The reflector was designed to:

- produce at most three reusable lessons;
- cite trajectory evidence;
- reason causally rather than merely describe the final fight;
- avoid confusing generated combat cards with permanent deck additions;
- avoid unsupported map claims;
- respect temporal information availability.

Validation showed that reflection can generate useful lessons but can also produce plausible yet strategically incorrect or overgeneralized conclusions. Those errors were intentionally preserved in autonomous Condition B.

---

## Condition B — pure autonomous self-reflection

**Status:** COMPLETE

**Dataset:** `spirecomm/runs/condition_b_self_reflection_30runs_final/`

**Configuration**

- agent: `self-reflection-condition-b-v1.0.0`
- model: `gpt-5.6-luna`
- character: Ironclad
- Ascension: 0
- completed runs: 30
- reflector: `reflection-v0.2`
- memory starts empty
- at most three new lessons per run
- retrieval: exact category, newest first, maximum three
- human semantic filtering: none

### Integrity

- 30 valid `RUN_END` events
- 30 completed reflections
- 85 stored lessons
- 0 malformed memory records
- 0 detected future-memory leakage

One extra `RUN_START` belonged to an interrupted physical run caused by a watchdog/readiness deadlock. It produced no completion or reflection and is excluded from the 30-run dataset.

### A vs B

| Metric | A | B |
|---|---:|---:|
| Wins | 0/30 | 0/30 |
| Mean floor | 23.37 | **27.23** |
| Median floor | 24 | **28** |
| Best floor | 50 | 50 |
| Mean score | 200.43 | **236.63** |
| Best score | **684** | 535 |
| Act 2 | 20/30 | **22/30** |
| Act 3 | 1/30 | **3/30** |

### Behaviour changes

Card reward selectivity increased substantially:

- A: 12 skips / 428 permanent card reward decisions = 2.8%
- B: 69 skips / 491 decisions = 14.1%

At campfires where HP was <=40% of maximum, Condition B rested in **27/29** cases.

### Memory

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

Gameplay LLM calls: 9,223. Calls with at least one retrieved memory: 8,542.

No retrieved lesson came from the current or a future run.

### Long-horizon limit

Condition B frequently acquired the Sapphire Key, but 0/30 runs ended with all three keys. Each Act-3 run lacked Emerald. This became a concrete example of learning a local decision rule without solving the longer planning problem.

### Interpretation

Autonomous reflection improved several local/medium-horizon behaviours but still produced 0 wins. The memory bank also accumulated near-duplicate lessons. Newest-first max-3 retrieval meant older valid knowledge could stop affecting gameplay.

**Decision:** freeze B as the autonomous top-3-memory study and investigate both human correction and a stronger shared memory interface.

---

## Condition C1 — human-curated reflection

**Status:** COMPLETE

**Dataset:** `spirecomm/runs/condition_c_human_feedback_30_runs/`

C1 preserved B's run-level reflection timing and retrieval interface but inserted human review before final memory storage.

The reviewer could:

- ACCEPT an initial lesson;
- CORRECT it;
- REJECT it;
- ADD a missed lesson.

### Final memory

73 retained final lessons:

| Category | Lessons |
|---|---:|
| COMBAT | 30 |
| CARD_REWARD | 17 |
| REST | 12 |
| EVENT | 8 |
| SHOP | 4 |
| GENERAL | 1 |
| BOSS_REWARD | 1 |

Retained provenance:

- 61 accepted;
- 11 corrected;
- 1 added.

Human corrections addressed wrong-cause attribution, missing strategic context, over-vague guidance, long-horizon planning, and false lessons.

### Limitation

C1 still used newest-first exact-category retrieval capped at three memories. Therefore a high-quality human correction could still fail to influence future play because it aged out or was stored under a category not used at the relevant later decision.

**Decision:** preserve C1 as proof that human semantic review can improve lesson quality, then create a matched B2/C2 follow-up using a stronger memory interface shared by both conditions.

---

# Phase II — B2/C2 cumulative-memory follow-up

## Shared memory architecture

Every final lesson is appended permanently to raw JSONL memory.

A cumulative playbook maintains compact rules containing:

- primary category;
- `applies_to`;
- `when`;
- `guidance`;
- `rationale`;
- confidence;
- `source_memory_ids`.

Validation requires every raw lesson ID to remain represented by at least one playbook rule.

Retrieval scans the entire playbook and returns every rule whose `applies_to` includes the current decision category, including GENERAL rules. There is no newest-three truncation.

---

## C2 smoke v0.1

**Status:** COMPLETE

Validated:

- trajectory generation;
- browser-based human review;
- initial reflection;
- human feedback;
- final lesson storage;
- cumulative playbook update;
- Run-2 retrieval of Run-1 knowledge only.

The smoke exposed cross-category loss: useful guidance could be consolidated under one primary category and therefore be unavailable in another decision context.

This led to `cumulative-playbook-v2` and `applies_to`.

---

## C2 smoke v0.2

**Status:** COMPLETE — 2 valid runs

Validated:

- Run 1 started with empty memory;
- six final lessons after two runs;
- final playbook updated through Run 2;
- complete raw-memory source coverage;
- no current/future leakage;
- live cross-category retrieval.

A REST-primary rule was successfully retrieved at a MAP decision through `applies_to`.

The smoke also exposed a CommunicationMod stale-state edge case after Smoke Bomb. A bounded transition guard was added before official collection.

---

## B2 smoke v0.2

**Status:** COMPLETE — 2 valid runs

Validated the autonomous counterpart:

- Run 1 empty memory;
- six raw lessons after two runs;
- seven playbook rules;
- complete source coverage;
- no current/future leakage;
- live cross-category retrieval;
- Smoke Bomb guard exercised successfully.

---

# Invalidated B2 v1.1.0

**Status:** INVALIDATED — provenance/debug only

The first official B2 cumulative-memory batch completed 15 runs but was invalidated after discovering a permanent-card-reward skip loop.

When the actor selected Skip, CommunicationMod could continue advertising the same card reward on the parent `COMBAT_REWARD` list. The controller reopened it, creating Skip -> reopen loops until a later call took a card or Singing Bowl.

Measured impact:

- 92 skip decisions;
- 19 affected reward instances;
- 9/15 affected runs;
- worst instance: 29 repeated skips;
- every affected instance eventually took a card/Singing Bowl.

Because the bug materially altered deck construction and future learning, this dataset cannot be used as the control.

### v1.1.1 fix

`card-reward-skip-guard-v1` tracks skipped permanent reward entries within the current reward flow. It never reopens the same declined reward while still allowing later distinct rewards, including multiple-card-reward cases such as Prayer Wheel.

B2 was restarted from empty memory.

---

# Final B2 v1.1.1

**Status:** COMPLETE / FROZEN

**Dataset:** `spirecomm/runs/B2_v1_1_1_15runs_final/`

Configuration:

- model: `gpt-5.6-luna`
- Ironclad A0
- seeds `260925001`...`260925015` in order
- autonomous reflection
- cumulative-playbook-v2
- full 15-run batch

### Results

| Metric | B2 v1.1.1 |
|---|---:|
| Wins | 0/15 |
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

### Integrity

- exactly 15 starts / 15 completions / 15 reflections;
- Run 1 empty memory;
- 2,924 retrievals;
- zero current/future leakage;
- complete raw-memory source coverage;
- 13 permanent card-reward skips with no reopen loop;
- two-card-reward skip/advance case validated;
- no runtime/CommunicationMod/watchdog failure invalidated a run.

B2 is the final autonomous control.

---

# C2 authoritative teaching redesign

The early C2 design passed human feedback through a second strategic LLM reviser. This was removed because it made the treatment a mixture of human feedback and LLM interpretation.

Final C2 uses `authoritative-human-teaching-v1`:

### `APPROVE_INITIAL`

Store the initial reflection lessons unchanged.

### `HUMAN_TEACHING`

Store the reviewer's natural-language teaching verbatim.

A metadata-only organizer may infer only:

- title;
- primary category;
- `applies_to`.

It may not paraphrase, summarize, correct, soften, expand, or otherwise rewrite strategic content.

Authoritative playbook rules are reconstructed deterministically from raw memory and validation requires actor-facing guidance to equal the stored human text.

---

# Invalidated C2 v1.2.0

**Status:** INVALIDATED — provenance/debug only

Run 1 completed with authoritative human teaching that explicitly discussed Neow/start-relic strategy. The text was stored correctly, but the metadata organizer omitted `GENERAL` from `applies_to`.

Because `NEOW_BLESSING` retrieval uses the `GENERAL` category, Run 2 did not retrieve the Run-1 teaching at Neow. The rule was later retrieved in another applicable context, showing that storage itself worked and the error was retrieval scope.

### v1.2.1 fix

- metadata prompt explicitly maps controller decisions to retrieval categories;
- deterministic safeguard adds `GENERAL` whenever human teaching explicitly mentions Neow or a starting-relic-to-boss-relic swap.

A dedicated two-run scope smoke verified that Run-1 authoritative Neow teaching was retrieved during Run-2 `NEOW_BLESSING` before official collection restarted.

---

# Final C2 v1.2.1

**Status:** COMPLETE / FROZEN

**Dataset:** `spirecomm/runs/C2_v1_2_1_15runs_final/`

Configuration:

- model: `gpt-5.6-luna`
- Ironclad A0
- same 15 matched seeds as B2, same order
- cumulative-playbook-v2
- authoritative human-teaching policy
- full 15-run batch

### Results

| Metric | C2 v1.2.1 |
|---|---:|
| Wins | 0/15 |
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

### Review distribution

- `HUMAN_TEACHING`: 10 runs
- `APPROVE_INITIAL`: 5 runs

### Integrity

- 15 starts / 15 completions / 15 reflections;
- exact requested seed order `260925001`...`260925015`;
- 3,705 memory retrievals;
- zero detected current-run or future-run leakage;
- complete raw-memory source coverage;
- all authoritative human teaching preserved verbatim through actor-facing playbook guidance;
- one transient API HTTP 500 recovered on attempt 2 without gameplay fallback;
- two out-of-range model action indexes used the controller's deterministic index fallback.

The two fallback events are retained as model-output/protocol failures and the affected runs were not selectively rerun.

---

# Final B2 vs C2 comparison

| Metric | B2 | C2 |
|---|---:|---:|
| Wins | 0/15 | 0/15 |
| Mean floor | 18.73 | **27.33** |
| Median floor | 16 | **23** |
| Best floor | 29 | **50** |
| Mean score | 144.60 | **251.47** |
| Median score | 112 | **197** |
| Best score | 251 | **629** |
| Act 2+ | 6/15 | **13/15** |
| Act 3 | 0/15 | **2/15** |

Matched-seed descriptive comparison:

- floor: C2 better on 11/15, B2 better on 4/15;
- mean paired floor difference: +8.60 for C2;
- score: C2 better on 10/15, B2 better on 5/15;
- mean paired score difference: +106.87 for C2.

Interpretation: C2 substantially improved survival depth and score, particularly by reducing early-game failures and reaching Act 3. Neither system won, so the evidence supports improved long-horizon progression rather than complete game mastery.

See `FINAL_B2_C2_ANALYSIS.md` for the consolidated interpretation and limitations.

---

# Phase III — planned extended learning and held-out evaluation

The controlled B2/C2 comparison is complete. B2 does not need to remain an active development branch; it has served its role as the autonomous control.

The selected architecture is C2.

Recommended next phase:

1. continue C2 human-guided learning on fresh seeds not used in A/B/C1/B2/C2 or smoke tests;
2. keep feedback and memory updates enabled during this learning phase;
3. freeze the resulting controller, raw memory, and playbook;
4. create a separate held-out seed set never seen during learning;
5. evaluate the frozen agent with feedback/reflection/memory updates disabled;
6. compare held-out performance against appropriate frozen controls.

Learning seeds and evaluation seeds must remain disjoint.

The final evaluation should answer whether the strategy accumulated through human teaching transfers to unseen runs, rather than whether the agent can continue adapting to the same trajectories used for feedback.
