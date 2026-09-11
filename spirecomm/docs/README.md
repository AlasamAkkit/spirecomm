# FYP Research Documentation

This folder contains the maintained research and engineering records for the Slay the Spire LLM self-reflection project.

## Canonical files

- `PROJECT_LOG.md` — major architectural, methodological, and project milestones.
- `EXPERIMENTS.md` — experimental conditions, batches, quantitative results, and evaluation protocol.
- `OBSERVATIONS.md` — research observations and failure categories, using stable IDs such as `OBS-020`.
- `CHANGELOG.md` — implementation changes to the controller, reflection pipeline, memory system, and experiment infrastructure.

The repository-level `README.md` gives the overall project summary and current research design.

## Source-of-truth rule

For a frozen experiment, the machine-readable source of truth is its `run_events.jsonl` file stored under a named directory in `spirecomm/runs/`.

Do not manually edit experimental JSONL files after collection.

Generated working files such as active logs, smoke-test memory, and live Condition B memory are ignored by Git until an experiment is intentionally frozen and archived.

## Documentation update rule

After a meaningful milestone:

1. Record implementation changes in `CHANGELOG.md`.
2. Add or update research findings in `OBSERVATIONS.md` when they affect interpretation of agent behaviour.
3. Record completed or planned experiment batches in `EXPERIMENTS.md`.
4. Add major architectural or methodological decisions to `PROJECT_LOG.md`.
5. Freeze completed experiment artifacts under `spirecomm/runs/<experiment_name>/` rather than duplicating raw logs elsewhere.

## Current experimental design

The project compares:

- **Condition A — Baseline:** no cross-run learning.
- **Condition B — Self-reflection:** after each completed run, the LLM generates at most three reusable lessons which are stored and retrieved in later runs.
- **Condition C — Human feedback:** same memory and retrieval pipeline as Condition B, but a human reviews/corrects the reflection before storage.

The central research question is:

> Where are the limits of self-reflective learning in an LLM game-playing agent, and how does human feedback help overcome those limits?
