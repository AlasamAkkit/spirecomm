# Slay the Spire LLM Self-Reflection FYP

This repository contains a Final Year Project investigating how far a human can teach a large-language-model (LLM) agent to play **Slay the Spire** through iterative trajectory feedback, reflection, and persistent strategic memory.

The project builds on `spirecomm` and ForgottenArbiter's CommunicationMod. A Python controller converts game states into a constrained legal action set, asks the LLM to choose among those actions, validates the choice, and sends the corresponding protocol command back to Slay the Spire.

## Research question

> To what extent can iterative human feedback improve the long-horizon decision-making of an LLM agent in Slay the Spire, compared with autonomous self-reflection under the same memory system?

The project has progressed through an initial three-condition study and now uses a matched B2/C2 follow-up. **B2 is the autonomous self-reflection control; C2 is the final human-taught system.** Both share the same cumulative memory architecture so the contribution of human feedback can be isolated.

## Experimental progression

| Condition | Cross-run learning | Status |
|---|---|---|
| **A — Baseline** | None | Complete — 30 valid runs |
| **B — Self-reflection (C1-era memory design)** | LLM reflection; newest relevant memories, max 3 | Complete — 30 valid runs |
| **C1 — Human-curated reflection** | Same reflection/memory structure as B, but human review edits the lessons before storage | Complete — 30 reviewed runs |
| **B2 — Autonomous control** | LLM reflection -> permanent raw memory -> cumulative playbook | **Complete — final v1.1.1 15-run control** |
| **C2 — Final human-taught system** | Initial LLM reflection -> trajectory-level human feedback -> revised reflection -> same cumulative playbook | **Official v1.1.1 collection next** |

The follow-up names **B2/C2** are used to distinguish the improved cumulative-memory experiment from the completed B/C1 study.

## Current project status

### Completed

- **Condition A baseline:** 30 valid Ironclad Ascension 0 runs using `baseline-v1.0.5`.
- **Condition B self-reflection:** 30 valid runs using `reflection-v0.2` and exact-category newest-first top-3 retrieval.
- **Condition C1 human feedback:** 30 runs completed with human review before final lessons were stored.
- **C1 final memory:** 73 retained human-curated lessons.
  - COMBAT: 30
  - CARD_REWARD: 17
  - REST: 12
  - EVENT: 8
  - SHOP: 4
  - GENERAL: 1
  - BOSS_REWARD: 1
- Among those 73 retained C1 lessons, provenance records show **61 accepted**, **11 corrected**, and **1 added** lesson.
- **C2 smoke v0.1:** two-run end-to-end trajectory-feedback smoke test completed successfully.
- **C2 smoke v0.2:** complete — two valid runs, six final lessons, cumulative-playbook-v2 updated through Run 2, full raw-memory source coverage, cross-category retrieval observed, and no current/future-run memory leakage.
- **B2 smoke v0.2:** complete — two valid runs, six self-reflection lessons, seven final playbook rules, complete raw-memory coverage, live cross-category retrieval, and no current/future-run leakage.
- **Smoke-v0.2 transition finding:** the stale post-Smoke-Bomb combat snapshot found in C2 was exercised again in B2; the new bounded transition guard handled it with five waits and no invalid-command error.
- **B2/C2 v1.1 implementation:** cumulative playbook v2 with cross-category `applies_to` retrieval is validated for both conditions.
- **Card-reward correctness finding:** the v1.1.0 controller reopened skipped permanent card rewards because CommunicationMod continued exposing them on the combat-reward list. In the completed B2 v1.1.0 batch this produced 92 Skip decisions across 19 reward instances; every affected instance eventually took a card/Singing Bowl. The dataset is retained only as diagnostic evidence and is not the final B2 control.
- **v1.1.1 hotfix:** tracks skipped card-reward entries per combat-reward flow so each distinct permanent card reward is processed at most once while still supporting multiple card rewards such as Prayer Wheel.

### Current next step

The corrected **B2 v1.1.1** control is complete and frozen under `spirecomm/runs/B2_v1_1_1_15runs_final/`. The next step is **C2 v1.1.1**, the final human-taught system, using the same 15 seeds in the same order and empty C2 memory.

The official controllers are:

- `spirecomm/test_connection_b2_v1_1_1.py`
- `spirecomm/test_connection_c2_v1_1_1.py`

Both use the same 15 seed strings in the same order.

## Final B2 v1.1.1 control results

Dataset: `spirecomm/runs/B2_v1_1_1_15runs_final/`

| Metric | B2 v1.1.1 |
|---|---:|
| Completed runs | 15 |
| Wins | 0 |
| Mean floor | 18.73 |
| Median floor | 16 |
| Best floor | 29 |
| Mean score | 144.60 |
| Best score | 251 |
| Reached Act 2 | 6/15 (40.0%) |
| Reached Act 3 | 0/15 (0.0%) |
| Raw lessons | 38 |
| Final playbook rules | 14 |

Integrity audit:

- exactly 15 `RUN_START` and 15 `RUN_END` events;
- requested seeds exactly `260925001` through `260925015` in order;
- all events use `followup-b2-v1.1.1`;
- Run 1 retrieved no learned memory;
- 2,924 memory retrievals with zero current/future-run leakage;
- every raw lesson ID is represented by the final playbook and there are no unknown source IDs;
- 15 completed post-run reflections and `updated_through_run = 15`;
- no logged runtime/CommunicationMod/watchdog errors;
- 13 permanent card-reward skips were registered and the old skip->reopen loop was not observed;
- a two-card-reward case successfully skipped the first reward and processed the second reward once;
- three invalid-index LLM responses used the controller's deterministic index-parser fallback; these were not API/infrastructure failures.

## Discarded B2 v1.1.0 diagnostic batch

This 15-run batch completed structurally, but it is **not used as the final control** because the card-reward skip loop altered gameplay. It is retained for debugging/provenance only.

| Metric | B2 official |
|---|---:|
| Completed runs | 15 |
| Wins | 0 |
| Mean floor | 28.07 |
| Median floor | 27 |
| Best floor | 50 |
| Mean score | 271.47 |
| Best score | 577 |
| Reached Act 2 | 11/15 (73.3%) |
| Reached Act 3 | 4/15 (26.7%) |

The batch produced 41 raw lessons and 16 playbook rules, but those learned memories were influenced by the card-skip bug and must not be reused for v1.1.1.

## Condition A vs Condition B

| Metric | Condition A | Condition B |
|---|---:|---:|
| Completed runs | 30 | 30 |
| Wins | 0 | 0 |
| Mean floor reached | 23.37 | **27.23** |
| Median floor reached | 24 | **28** |
| Best floor | 50 | 50 |
| Mean score | 200.43 | **236.63** |
| Best score | **684** | 535 |
| Reached Act 2 | 20/30 (66.7%) | **22/30 (73.3%)** |
| Reached Act 3 | 1/30 (3.3%) | **3/30 (10.0%)** |

Condition B progressed farther on average but still produced **0 wins in 30 runs**.

Observed behavioural changes included:

- permanent card-reward skip rate increasing from **2.8%** to **14.1%**;
- low-HP campfire behaviour becoming substantially more conservative, with Rest chosen in **27/29** campfires at or below 40% maximum HP;
- Act 3 being reached three times instead of once;
- local Sapphire Key behaviour improving, while **0/30** runs still finished with all three keys.

These results motivated the hypothesis that autonomous reflection is better at correcting repeated local/medium-horizon mistakes than at solving long-horizon planning and credit assignment.

## Why the B2/C2 follow-up exists

The first B/C1 memory design had two important limitations.

### 1. Rolling top-3 memory

Condition B/C1 retrieved only the newest matching lessons, with a maximum of three. Older useful lessons could therefore stop affecting gameplay even though they remained valid.

### 2. Category isolation

Lessons were stored under one category. A lesson learned from an EVENT could contain useful CARD_REWARD guidance, but exact-category retrieval could make that guidance invisible during later card-reward decisions.

The C2 smoke-v0.1 run exposed this directly: human feedback about deck selectivity was consolidated partly into an EVENT rule, so that advice was not guaranteed to appear during CARD_REWARD decisions.

### v1.1 solution: cumulative playbook v2

B2 and C2 retain every final raw lesson permanently and consolidate the complete lesson history into a cumulative playbook.

Each playbook rule contains:

- a primary category;
- `applies_to` decision categories;
- `when`;
- `guidance`;
- `rationale`;
- confidence;
- `source_memory_ids`.

Every raw lesson ID must remain represented by at least one playbook rule. The actor then receives **all applicable playbook rules** for the current decision rather than only the newest three lessons.

This creates a cleaner B2/C2 comparison:

```text
B2
completed trajectory
    -> LLM reflection
    -> final lessons
    -> cumulative playbook
    -> future decisions

C2
completed trajectory
    -> initial LLM reflection
    -> human trajectory feedback
    -> LLM revised reflection
    -> final lessons
    -> same cumulative playbook
    -> future decisions
```

The intended treatment difference is therefore the **human trajectory feedback**, not a different gameplay controller or memory capacity.

## System architecture

```text
Slay the Spire
      |
      v
CommunicationMod JSON
      |
      v
Python controller
  - state parsing
  - legal action generation
  - deterministic/forced actions
  - logging / watchdog recovery
      |
      v
LLM actor
      |
      v
validated legal action
      |
      v
CommunicationMod command
      |
      v
Slay the Spire
```

For B2/C2 the learning loop is:

```text
completed run
    |
    v
compact trajectory
    |
    v
initial reflection
    |
    +---- B2: use directly
    |
    +---- C2: human trajectory feedback -> revised reflection
    |
    v
permanent raw lessons
    |
    v
cumulative playbook
    |
    v
all applicable rules injected into future decisions
```

## Controller and experiment safeguards

The current controller:

- exposes only legal actions to the LLM;
- handles combat, events, rewards, shops, campfires, GRID/HAND_SELECT screens, potions, keys, boss relics, and terminal states;
- keeps stdout reserved for CommunicationMod commands;
- separates infrastructure failures from gameplay reasoning failures;
- retries transient LLM API failures but **does not substitute gameplay fallbacks** after API failure;
- pauses the experiment if reflection/memory updating fails;
- recovers completed-but-unreflected runs before allowing a new run;
- validates raw-memory/playbook alignment on startup;
- uses a watchdog when CommunicationMod does not return a command-ready state.

The controller does not train model weights. Learning occurs through reflection-derived external memory injected into later prompts.

## Repository structure

```text
.
├── README.md
├── reflection/
│   ├── prepare_reflection.py
│   ├── reflect_run.py
│   ├── condition_c_reflection.py
│   ├── review_condition_c.py
│   ├── followup_reflection.py
│   ├── feedback_app.py
│   └── historical prototype memory scripts
│
└── spirecomm/
    ├── test_connection.py
    ├── test_connection_b2_smoke_v0_2.py
    ├── test_connection_c2_smoke_v0_2.py
    ├── test_connection_b2_v1_1_0.py
    ├── test_connection_c2_v1_1_0.py
    ├── FOLLOWUP_B2_C2_V1_1_PROTOCOL.md
    ├── spirecomm/
    ├── utilities/
    ├── docs/
    └── runs/
        ├── baseline_v1_30runs_final/
        ├── condition_b_self_reflection_30runs_final/
        ├── condition_c_human_feedback_30_runs/
        └── C2_B2_smoke_v0.1runs/
```

Versioned controller files are kept so experiment builds remain reproducible. CommunicationMod launches `spirecomm/test_connection.py`; the chosen versioned controller is copied over that filename when starting a smoke or official experiment.

## Key experimental controls

For the B2/C2 matched follow-up:

- model: `gpt-5.6-luna`;
- character: Ironclad;
- Ascension: 0;
- 15 fixed matched seeds per condition;
- same gameplay controller logic;
- same reflection schema and cumulative playbook mechanism;
- B2 and C2 memories/output files are isolated;
- smoke memories are never carried into official runs;
- reflection completes before a later run starts;
- no future-run memory is available to earlier decisions;
- infrastructure-interrupted attempts do not count as valid completed runs;
- C2 human feedback is written only after inspecting the completed trajectory.

## Research records

Project documentation lives in `spirecomm/docs/`:

- `PROJECT_LOG.md` — major implementation and methodological milestones.
- `EXPERIMENTS.md` — experimental conditions, completed batches, and follow-up protocol.
- `OBSERVATIONS.md` — research observations and failure categories.
- `CHANGELOG.md` — controller/reflection/memory implementation changes.

The machine-readable gameplay source of truth for a frozen experiment is its structured event log.

## Requirements

The gameplay setup uses:

- Slay the Spire
- ModTheSpire
- BaseMod
- CommunicationMod
- Python with the local `spirecomm` package
- OpenAI Python SDK and an `OPENAI_API_KEY`

## Acknowledgement

The communication layer is based on the open-source `spirecomm` project and ForgottenArbiter's CommunicationMod. The FYP work in this repository extends that base with the autonomous LLM controller, structured experiment logging, reflection and memory pipelines, human-feedback workflows, and comparative learning-study design.
