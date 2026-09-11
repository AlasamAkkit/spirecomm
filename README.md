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
- **Reflection mechanism:** `reflection-v0.2` validated offline on held-out baseline trajectories.
- **Memory retrieval:** validated with category-based retrieval and a maximum of three lessons per decision.
- **Online learning loop:** validated in a two-run smoke test (`Run 1 -> reflection -> memory -> Run 2`).
- **Condition B:** implementation validated and ready for 30-run data collection.
- **Condition C:** planned after Condition B using the same controller, memory schema, retrieval limits, and reflection timing, with human curation as the controlled difference.

## Baseline results

The final baseline dataset contains **30 completed runs**.

| Metric | Result |
|---|---:|
| Wins | 0 / 30 |
| Mean floor reached | 23.37 |
| Median floor reached | 24 |
| Best floor | 50 |
| Mean score | 200.43 |
| Best score | 684 |
| Reached Act 2 | 20 / 30 (66.7%) |
| Reached Act 3 | 1 / 30 (3.3%) |
| Total LLM calls | 6,798 |
| Total input + output tokens | 7,663,520 |
| Mean LLM latency | 6.85 s |

The main gameplay bottleneck was **mid-Act-2 attrition and resource/risk management**, rather than a single controller failure. Frequent strategic patterns included low-HP smithing, limited card skipping, deck growth, potion/resource timing, and repeated deaths to Act 2 elites/hallway fights.

The canonical baseline dataset is stored at:

```text
spirecomm/runs/baseline_v1_30runs_final/
```

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
        ├── baseline_v1_30runs_final/
        └── ... development/smoke run archives
```

Generated runtime logs and active experiment memory are intentionally ignored by Git. Once an experiment is frozen, the selected research artifacts can be copied into a named folder under `spirecomm/runs/`.

## Key experimental controls

To keep comparisons interpretable:

- the actor model, game character, Ascension level, legal-action controller, and decision interfaces are kept fixed across experimental conditions as far as practical;
- reflection occurs **once after a completed run**, not after every action;
- Condition B stores the LLM's lessons automatically without human semantic filtering;
- Condition C changes only the lesson curation source after reflection;
- memory retrieval is restricted to relevant decision categories and at most three lessons;
- lessons from the current/future run are never available to earlier decisions;
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

CommunicationMod should invoke the Python controller directly. Runtime protocol output is kept on stdout; research/debug output is written to files.

## Acknowledgement

The communication layer is based on the open-source `spirecomm` project and ForgottenArbiter's CommunicationMod. The FYP work in this repository extends that base with the autonomous LLM controller, experiment logging, baseline evaluation, reflection pipeline, memory retrieval, and comparative learning-study design.
