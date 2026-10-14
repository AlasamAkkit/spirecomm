# Experiment Ledger

This document records the experimental progression of the Slay the Spire LLM FYP. It separates the **completed controlled experiments** from the later **exploratory continual-teaching phase**.

## Overview

| Stage | Conditions / run range | Purpose | Status |
|---|---|---|---|
| Phase I | A, B, C1 | Establish baseline, autonomous reflection, and human-curated reflection behavior | Complete / frozen |
| Phase II | B2 vs C2 | Matched cumulative-memory comparison of autonomous reflection vs authoritative human teaching | Complete / frozen |
| Continual C2 | Runs 16+ | Explore how continued teaching and architecture changes affect long-horizon behavior | Active; finalized through Run 33 |

The controlled B2/C2 comparison is the primary causal comparison. Continual-C2 runs are **not** pooled into that analysis because the controller architecture changes across explicit intervention boundaries.

---

# Phase I — A / B / C1

## Condition A — no-memory baseline

**Dataset:** `spirecomm/runs/baseline_v1_30runs_final/`

Configuration:

- Ironclad;
- Ascension 0;
- GPT-5.6 Luna actor;
- no cross-run memory;
- 30 valid completed runs.

| Metric | A |
|---|---:|
| Wins | 0/30 |
| Mean floor | 23.37 |
| Median floor | 24 |
| Best floor | 50 |
| Mean score | 200.43 |
| Best score | 684 |
| Act 2 | 20/30 |
| Act 3 | 1/30 |

Permanent card rewards were skipped 12/428 times (2.8%).

**Role:** establishes starting capability without cross-run learning.

## Condition B — autonomous self-reflection

**Dataset:** `spirecomm/runs/condition_b_self_reflection_30runs_final/`

Learning design:

```text
completed run
 -> reflection-v0.2
 -> up to 3 lessons
 -> exact-category newest-first memory
 -> max 3 retrieved lessons per decision
```

No human semantic filtering.

Integrity:

- 30 valid completed runs;
- 30 completed reflections;
- 85 stored lessons;
- zero detected future-memory leakage.

| Metric | A | B |
|---|---:|---:|
| Wins | 0 | 0 |
| Mean floor | 23.37 | **27.23** |
| Median floor | 24 | **28** |
| Mean score | 200.43 | **236.63** |
| Act 2 | 20/30 | **22/30** |
| Act 3 | 1/30 | **3/30** |

Behavioral change:

- permanent card skip rate increased from 2.8% to 14.1%;
- at campfires with HP <=40% max, B rested in 27/29 cases.

Limitations exposed:

1. older lessons age out of the newest-three window;
2. one primary category can hide cross-category guidance;
3. autonomous reflection can misattribute causes or store duplicated/weak lessons;
4. local rules do not automatically solve long-horizon planning such as Emerald-key routing.

## Condition C1 — human-curated reflection

**Dataset:** `spirecomm/runs/condition_c_human_feedback_30_runs/`

C1 retained B's original retrieval structure but inserted human review before storage.

Reviewer operations included ACCEPT / CORRECT / REJECT / ADD-style intervention.

Final retained memory: 73 lessons.

| Category | Count |
|---|---:|
| COMBAT | 30 |
| CARD_REWARD | 17 |
| REST | 12 |
| EVENT | 8 |
| SHOP | 4 |
| GENERAL | 1 |
| BOSS_REWARD | 1 |

Retained provenance:

- accepted: 61;
- corrected: 11;
- human-added: 1.

**Finding:** human review can correct causal attribution, missing context, vague guidance, and false strategic conclusions, but the original newest-three/exact-category retrieval still limits whether good teaching reaches future decisions.

---

# Phase II — matched B2/C2 cumulative-memory follow-up

## Shared memory architecture

B2 and C2 use `cumulative-playbook-v2`.

Every final lesson remains in permanent raw memory. The playbook indexes rules containing:

- primary category;
- `applies_to`;
- `when`;
- `guidance`;
- `rationale`;
- confidence;
- `source_memory_ids`.

Validation requires every raw lesson ID to remain represented by at least one rule.

During the matched experiment, retrieval supplies all applicable rules rather than only the newest three.

## Matched controls

Final B2/C2 used:

- model: GPT-5.6 Luna;
- Ironclad;
- Ascension 0;
- same 15 seeds in the same order;
- same legal-action/controller interface;
- same cumulative-memory architecture;
- condition-specific memory/log files;
- reflection completion before the next run.

Official seed order:

```text
260925001
260925002
260925003
260925004
260925005
260925006
260925007
260925008
260925009
260925010
260925011
260925012
260925013
260925014
260925015
```

## B2 v1.1.0 — invalidated

The first 15-run B2 cumulative-memory batch was invalidated because a skipped permanent card reward could reopen from the parent reward screen.

Impact:

- 92 skip decisions;
- 19 affected reward instances;
- 9 affected runs;
- worst case 29 repeated skips;
- affected reward flows eventually took a card or Singing Bowl.

Archive:

```text
spirecomm/runs/B2_v1_1_0_invalidated_card_skip_bug/
```

The corrected v1.1.1 control restarted from empty memory.

## B2 v1.1.1 — final autonomous control

**Dataset:** `spirecomm/runs/B2_v1_1_1_15runs_final/`

| Metric | B2 |
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

Integrity:

- 15 starts / 15 ends / 15 reflections;
- exact seed order;
- Run 1 memory empty;
- 2,924 memory retrievals;
- zero detected current/future leakage;
- complete raw-memory source coverage;
- permanent card Skip guard behaved correctly.

## C2 authoritative-teaching design

C2 originally tested an extra LLM that rewrote human feedback. That design was removed because it made attribution ambiguous.

Final policy:

```text
authoritative-human-teaching-v1
```

Review outcomes:

- `APPROVE_INITIAL` — store initial reflection lessons unchanged;
- `HUMAN_TEACHING` — store human strategy verbatim.

For human teaching, the metadata model may infer only title, primary category, and `applies_to`. It may not rewrite strategic content.

## C2 v1.2.0 — invalidated

Run-1 human teaching mentioned Neow/start-relic strategy but its metadata omitted `GENERAL`, so Run 2 did not retrieve it at `NEOW_BLESSING`.

Archive:

```text
spirecomm/runs/C2_v1_2_0_invalidated_metadata_scope_bug/
```

v1.2.1 added explicit controller-category mapping and a deterministic `GENERAL` scope safeguard for Neow/start-relic teaching. A dedicated scope smoke passed before official collection.

## C2 v1.2.1 — final human-taught treatment

**Dataset:** `spirecomm/runs/C2_v1_2_1_15runs_final/`

| Metric | C2 |
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

Review distribution:

- `HUMAN_TEACHING`: 10;
- `APPROVE_INITIAL`: 5.

Integrity:

- 15 starts / 15 ends / 15 reflections;
- exact seed order;
- 3,705 memory retrievals;
- zero detected current/future leakage;
- complete raw-memory source coverage;
- all authoritative human teaching preserved verbatim in actor-facing guidance.

## Final B2 vs C2 comparison

| Metric | B2 | C2 |
|---|---:|---:|
| Wins | 0 | 0 |
| Mean floor | 18.73 | **27.33** |
| Median floor | 16 | **23** |
| Best floor | 29 | **50** |
| Mean score | 144.60 | **251.47** |
| Median score | 112 | **197** |
| Best score | 251 | **629** |
| Act 2+ | 6/15 | **13/15** |
| Act 3 | 0/15 | **2/15** |

Paired direction:

- C2 higher floor on 11/15 seeds;
- B2 higher floor on 4/15;
- mean paired floor gain: `+8.60` for C2;
- C2 higher score on 10/15;
- B2 higher score on 5/15;
- mean paired score gain: `+106.87` for C2.

Supported interpretation:

> Authoritative human teaching improved survival depth and long-horizon progression under the matched cumulative-memory design.

Neither condition won, so the result should not be described as solving Slay the Spire.

Canonical protocol: `protocols/B2_C2_FINAL_PROTOCOL.md`  
Final analysis: `FINAL_B2_C2_ANALYSIS.md`

---

# Continual C2 — exploratory longitudinal phase

The original proposal for a fixed additional teaching block followed by held-out frozen evaluation was superseded. The project instead follows one continuously taught C2 agent across fresh seeds and explicit controller interventions.

Rules:

- start from the accepted C2 Run-15 state;
- fresh unique random seed per run;
- same memory persists across continual runs;
- human review after every completed run;
- remain at Ascension 0 until the first win, then advance;
- document every controller architecture change as a separate boundary.

## Runs 16–28 — continual v1.0

Inherited the original one-action decision architecture while continuing C2 teaching.

Checkpoint:

```text
spirecomm/runs/C2_continual_v1_0_through_run28/
```

By Run 28, repeated teaching had exposed persistent card-selection, deck-coherence, and combat-ordering failures. This motivated an architecture intervention rather than simply accumulating more advice.

## Runs 29–32 — v1.1.1 card priors + first turn planner

Controller:

```text
c2-continual-teaching-v1.1.1-card-prior-turn-planner
```

Added:

- fixed expert Ironclad card priors;
- explicit permanent reward scoring including Skip;
- a proposed whole-turn combat sequence.

Limitation:

- after executing the first action, the controller replanned from scratch;
- Run 32 demonstrated that the second plan could contradict the original defensive sequence.

Pre-v1.2 checkpoint:

```text
spirecomm/runs/C2_continual_through_run32_pre_v1_2/
```

Validated at checkpoint:

- 32 completed/reflected runs;
- 46 raw lessons;
- 32 playbook rules;
- 32 feedback rows.

## Run 33 — v1.2.0 persistent planning

Controller:

```text
c2-continual-teaching-v1.2.0-persistent-planning
```

Architecture:

```text
persistent-deck-plan+sticky-turn-plan+focused-memory-v1
```

Added:

- persistent run-level deck plan;
- deterministic card-score argmax with Skip winning ties;
- sticky within-turn plan continuation;
- bounded focused memory for COMBAT (8) and permanent CARD_REWARD (10).

Run 33 outcome:

- LOSS;
- Act 2 Floor 33;
- score 292;
- Collector.

Observed improvements:

- multi-action combat ordering was actually followed;
- card skipping became more deliberate later in the run;
- tactical prompt growth decreased.

Remaining issues:

- the deck planner could identify scaling as the main weakness yet still prefer a locally efficient attack over an offered scaling tool;
- focused-memory v1 ranking could hide a recent cross-category authoritative lesson.

## Run 34+ — v1.2.1 retrieval hotfix

Intended controller:

```text
c2-continual-teaching-v1.2.1-applicability-recency-hotfix
```

The hotfix preserves v1.2 persistent planning and changes focused-memory ranking to prefer recent applicable authoritative teaching before primary-category metadata.

Canonical continual protocol: `protocols/C2_CONTINUAL_TEACHING_PROTOCOL.md`  
Live status: `CONTINUAL_C2_STATUS.md`  
Controller mapping: `CONTROLLER_HISTORY.md`

---

# Analysis boundaries

Use these rules when writing the report:

1. **Phase I** can be discussed as the initial behavioral study.
2. **Phase II B2/C2** is the controlled matched comparison and should remain frozen.
3. **Continual C2** is exploratory/longitudinal and should be analyzed by controller era.
4. Do not mix invalidated/smoke datasets into performance tables.
5. Do not claim a continual architecture change was active before its logged run boundary.
6. Use structured event metadata, not the current active `test_connection.py`, to attribute controller version to an old run.
