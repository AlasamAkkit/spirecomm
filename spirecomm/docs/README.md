# FYP Research Documentation

This folder contains the maintained research and engineering records for the Slay the Spire LLM self-reflection project.

## Canonical files

- `PROJECT_LOG.md` — major architectural, methodological, and project milestones.
- `EXPERIMENTS.md` — experimental conditions, completed batches, quantitative results, and evaluation protocol.
- `OBSERVATIONS.md` — research observations and failure categories, using stable IDs such as `OBS-044`.
- `CHANGELOG.md` — implementation changes to the controller, reflection pipeline, memory system, and experiment infrastructure.

The repository-level `README.md` gives the overall project summary and current research design.

## Source-of-truth rule

For a frozen experiment, the machine-readable source of truth is its structured event log stored with the archived experiment artifacts under `spirecomm/runs/`.

Do not manually edit experimental JSONL files after collection.

Active working logs, smoke-test memory, and live experiment memory should remain isolated from frozen datasets. Once a run batch is accepted as final, archive the selected controller and research artifacts under a named directory in `spirecomm/runs/`.

## Documentation update rule

After a meaningful milestone:

1. record implementation changes in `CHANGELOG.md`;
2. add or update behavioural findings in `OBSERVATIONS.md`;
3. record experiment batches and controls in `EXPERIMENTS.md`;
4. add major architectural or methodological decisions to `PROJECT_LOG.md`;
5. freeze completed experiment artifacts under `spirecomm/runs/<experiment_name>/`.

## Current experimental status

- **Condition A — Baseline:** complete, 30 valid runs.
- **Condition B — Self-reflection:** complete, 30 valid runs with 85 stored self-generated lessons.
- **Condition C1 — Human-curated reflection:** complete, 30 reviewed runs with 73 retained curated lessons.
- **C2 smoke v0.1:** complete, 2 runs.
- **C2 smoke v0.2:** complete, 2 valid runs; cumulative-playbook-v2, source coverage, cross-category retrieval, and temporal isolation verified.
- **B2 smoke v0.2:** complete, 2 valid runs; six raw self-reflection lessons, seven final playbook rules, cross-category retrieval, source coverage, and temporal isolation verified.
- **B2/C2 v1.1.1:** matched controllers use cumulative-playbook-v2, the Smoke Bomb transition guard, and the permanent card-reward skip guard.
- **Final framing:** B2 is the autonomous self-reflection control; C2 is the final human-taught system.
- **B2 official v1.1.1:** complete — 15 valid matched runs; final frozen control is `spirecomm/runs/B2_v1_1_1_15runs_final/`.
- **C2 official v1.2.0:** next — same 15 seeds and empty C2 memory. Human review either approves the initial reflection unchanged or supplies authoritative teaching stored verbatim.

## Experimental progression

### A — Baseline

No cross-run learning.

### B — Pure self-reflection

After each run, `reflection-v0.2` generates at most three lessons. Later decisions retrieve the newest matching lessons, capped at three.

### C1 — Human-curated reflection

The initial reflection is reviewed by a human using ACCEPT/CORRECT/REJECT/ADD-style intervention. Final curated lessons are stored in the same general top-3 memory design.

### B2 — Autonomous self-reflection control

Final self-reflection lessons are retained permanently in raw memory and consolidated into a cumulative playbook. The actor receives all playbook rules whose `applies_to` scope includes the current decision category.

### C2 — Final human-taught system

The same cumulative-memory architecture is used, but the human is the authoritative strategy source. After each run, the reviewer either approves the initial LLM reflection unchanged or supplies natural-language teaching that is stored verbatim. An LLM may organize retrieval metadata only; it may not rewrite the human's strategic content.

B2 and C2 use the same 15 official seeds in the same order so the final analysis can include paired per-seed comparisons.

## Central research question

> To what extent can iterative human feedback improve the long-horizon decision-making of an LLM agent in Slay the Spire, compared with autonomous self-reflection under the same memory system?
