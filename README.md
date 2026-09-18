# Slay the Spire LLM Self-Reflection FYP

This repository contains a Final Year Project investigating whether a large-language-model (LLM) agent can improve at **Slay the Spire** by learning from previous gameplay experience, and where autonomous self-reflection still fails compared with human-guided feedback.

The project builds on `spirecomm` and ForgottenArbiter's CommunicationMod to connect Slay the Spire to a Python controller. The controller exposes only legal actions to the LLM, validates the selected action, and sends the corresponding protocol command back to the game.

## Research question

> Where are the limits of self-reflective learning in an LLM game-playing agent, and how does human feedback help overcome those limits?

The experimental design compares three conditions:

| Condition | Cross-run learning | Description |
|---|---|---|
| **A — Baseline** | None | Each run is independent. No previous-run lessons are available to the actor. |
| **B — Self-reflection** | LLM-generated | After each completed run, a reflector extracts at most three reusable lessons. Later decisions retrieve relevant prior lessons. |
| **C — Human feedback** | Human-curated LLM reflection | Uses the same memory/retrieval pipeline as Condition B, but a human reviews and corrects the generated lessons before they are stored. |

The goal is not only to compare performance, but to identify **which kinds of mistakes autonomous reflection can correct, which mistakes persist, and exactly how human feedback helps**.

## Current project status

- **Condition A baseline:** complete — 30 valid Ironclad Ascension 0 runs using `baseline-v1.0.5`.
- **Condition B self-reflection:** complete — 30 valid runs using the frozen reflection/memory pipeline.
- **Reflection mechanism:** `reflection-v0.2`, validated offline and then used without human semantic filtering in Condition B.
- **Memory retrieval:** exact-category retrieval, newest-first, maximum three lessons per decision.
- **Condition C:** next planned experiment; it will keep the same learning architecture while adding post-run human curation before lessons are stored.

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

Condition B progressed farther on average but still produced **0 wins in 30 runs**. The current interpretation is therefore not simply that self-reflection "solved" the task. Instead, self-reflection appears to improve some recurring local/medium-horizon behaviours while leaving important long-horizon planning and credit-assignment problems unresolved.

### Behavioural changes observed in Condition B

- Permanent card-reward skip rate increased from **2.8%** in the baseline to **14.1%**.
- Low-HP campfire decisions became much more conservative: at campfires where HP was at or below 40% of maximum, Condition B rested in **27 of 29** cases.
- Act 3 was reached three times instead of once.
- Deaths shifted away from some hallway/elite attrition toward later boss encounters, consistent with deeper average progression.
- The agent became good at preserving/collecting the Sapphire Key locally, but still ended **0 runs with all three keys**, showing that long-horizon key planning remained weak.

These patterns support the current hypothesis that autonomous reflection is better at correcting **repeated local mistakes** than at building a coherent long-horizon strategy.

## Condition B memory results

The 30-run self-reflection condition produced:

- **85 stored lessons**
- **9,223 gameplay LLM calls**
- **8,542 calls with at least one retrieved memory**
- **681 calls with no retrieved memory**
- **0 detected future-memory leakage**
- **30 post-run reflection completions for 30 completed runs**

Lesson categories:

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

A recurring pattern was that the reflector often rediscovered variants of the same advice, especially around low-HP survival and avoiding marginal card additions. This suggests that the system can identify recurring symptoms, but does not always consolidate them into a deeper cumulative strategy.

## System architecture

```text
Slay the Spire
      |
      v
CommunicationMod JSON
      |
      v
Python controller
  - state formatting
  - legal action generation
  - deterministic/forced actions
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

For the self-reflection condition, the run-level learning loop adds:

```text
completed run
    |
    v
compact trajectory
    |
    v
Reflector (reflection-v0.2)
    |
    v
<= 3 reusable lessons
    |
    v
memory.jsonl
    |
    v
category-based retrieval
    |
    v
future actor decisions
```

When no relevant memory exists, the gameplay prompt is left unchanged so an empty-memory run remains equivalent to the baseline policy.

## Repository structure

```text
.
├── README.md
├── .gitignore
├── reflection/
│   ├── prepare_reflection.py
│   ├── reflect_run.py
│   ├── build_prototype_memory.py
│   └── retrieve_memories.py
│
└── spirecomm/
    ├── test_connection.py
    ├── spirecomm/
    ├── utilities/
    ├── docs/
    │   ├── README.md
    │   ├── PROJECT_LOG.md
    │   ├── EXPERIMENTS.md
    │   ├── OBSERVATIONS.md
    │   └── CHANGELOG.md
    └── runs/
        └── baseline_v1_30runs_final/
```

Generated runtime logs and active experiment memory are intentionally ignored by Git. Once an experiment is frozen, selected research artifacts can be copied into a named folder under `spirecomm/runs/`.

## Key experimental controls

To keep comparisons interpretable:

- the actor model, character, Ascension level, legal-action controller, and decision interfaces are kept fixed across conditions as far as practical;
- reflection occurs **once after a completed run**, not after every action;
- Condition B stores the LLM's lessons automatically without human semantic filtering;
- Condition C changes the lesson curation stage while preserving the rest of the learning pipeline;
- memory retrieval is restricted to the matching decision category and at most three lessons;
- lessons from the current or future run are never available to earlier decisions;
- controller/interface failures are logged separately from LLM reasoning failures.

## Research records

Project documentation lives in `spirecomm/docs/`:

- `PROJECT_LOG.md` — major implementation and methodological milestones.
- `EXPERIMENTS.md` — experimental conditions, batches, and quantitative results.
- `OBSERVATIONS.md` — research observations and failure categories.
- `CHANGELOG.md` — controller/reflection implementation changes.

The machine-readable gameplay source of truth for a frozen experiment is its `run_events.jsonl` file.

## Requirements

The gameplay setup uses:

- Slay the Spire
- ModTheSpire
- BaseMod
- CommunicationMod
- Python with the local `spirecomm` package
- OpenAI Python SDK and an `OPENAI_API_KEY` for LLM calls

CommunicationMod invokes the Python controller directly. Runtime protocol output is kept on stdout; research/debug output is written to files.

## Acknowledgement

The communication layer is based on the open-source `spirecomm` project and ForgottenArbiter's CommunicationMod. The FYP work in this repository extends that base with the autonomous LLM controller, experiment logging, baseline evaluation, reflection pipeline, memory retrieval, and comparative learning-study design.
