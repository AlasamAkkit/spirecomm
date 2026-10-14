# FYP Research Documentation

This directory is the canonical documentation hub for the Slay the Spire LLM self-reflection / human-teaching FYP.

The documentation is intentionally split into **frozen controlled-phase records**, **active continual-phase records**, and **engineering/reference documents** so later controller changes do not overwrite the interpretation of earlier experiments.

## Start here

### Current project status

- [`CONTINUAL_C2_STATUS.md`](CONTINUAL_C2_STATUS.md) — live longitudinal status through the latest finalized checkpoint.
- [`CONTROLLER_HISTORY.md`](CONTROLLER_HISTORY.md) — exact mapping from run ranges to controller versions and intervention boundaries.
- [`PROJECT_LOG.md`](PROJECT_LOG.md) — chronological research and architecture milestones.

### Protocols

Canonical protocols live in [`protocols/`](protocols/):

- [`protocols/B2_C2_FINAL_PROTOCOL.md`](protocols/B2_C2_FINAL_PROTOCOL.md) — completed/frozen matched B2/C2 experiment.
- [`protocols/C2_CONTINUAL_TEACHING_PROTOCOL.md`](protocols/C2_CONTINUAL_TEACHING_PROTOCOL.md) — active open-ended continual-C2 protocol.

The old root-level protocol filenames are retained only as compatibility pointers.

### Controlled experiment analysis

- [`FINAL_B2_C2_ANALYSIS.md`](FINAL_B2_C2_ANALYSIS.md) — final matched comparison and integrity summary.
- [`EXPERIMENTS.md`](EXPERIMENTS.md) — broader condition definitions, datasets, quantitative results, and protocol history.

### Engineering / learning-system reference

- [`LEARNING_PIPELINE.md`](LEARNING_PIPELINE.md) — reflection, human review, raw memory, playbook, retrieval, and continual-planning flow.
- [`HUMAN_FEEDBACK_MECHANISM.md`](HUMAN_FEEDBACK_MECHANISM.md) — how human review is represented and preserved.
- [`LOGGING_SCHEMA.md`](LOGGING_SCHEMA.md) — structured logging conventions and event fields.
- [`REPO_FILE_GUIDE.md`](REPO_FILE_GUIDE.md) — repository layout and source-of-truth guide.

### Historical engineering records

- [`OBSERVATIONS.md`](OBSERVATIONS.md) — stable observation/failure IDs.
- [`CHANGELOG.md`](CHANGELOG.md) — implementation/research infrastructure changes.
- [`M1_4_REFLECTION_PIPELINE.md`](M1_4_REFLECTION_PIPELINE.md) — earlier reflection-pipeline milestone record; useful historically, not the active continual protocol.

## Current research status

### Controlled B2/C2 comparison — complete

| Metric | B2 autonomous | C2 human-taught |
|---|---:|---:|
| Runs | 15 | 15 |
| Wins | 0 | 0 |
| Mean floor | 18.73 | **27.33** |
| Median floor | 16 | **23** |
| Best floor | 29 | **50** |
| Mean score | 144.60 | **251.47** |
| Act 2+ | 6/15 | **13/15** |
| Act 3 | 0/15 | **2/15** |

Paired matched-seed direction:

- C2 higher floor on 11/15 seeds; mean paired gain `+8.60` floors;
- C2 higher score on 10/15 seeds; mean paired gain `+106.87` points.

This analysis is frozen. Continual-C2 runs must not be added to the controlled comparison.

### Continual C2 — active

Latest finalized checkpoint:

```text
Run 33
Ascension 0
Result: LOSS, Act 2 Floor 33, score 292, Collector
```

Controller chronology:

```text
Runs 16-28  -> continual v1.0
Runs 29-32  -> v1.1.1 card prior + replan-every-action turn planner
Run 33      -> v1.2.0 persistent deck plan + sticky turn plan + focused memory
Run 34+     -> v1.2.1 applicability/recency focused-memory hotfix
```

The continual phase is exploratory/longitudinal. Architecture changes are allowed when evidence exposes a concrete bottleneck, but every intervention gets an explicit version boundary and is analyzed separately.

## Source-of-truth rules

For frozen experiments, the machine-readable structured event log stored with the archived artifacts under `spirecomm/runs/` is the runtime source of truth.

For active continual C2:

- `spirecomm/run_events_c2.jsonl` records runtime decisions and controller metadata;
- `reflection/condition_c2_raw_memory.jsonl` is the authoritative lesson provenance store;
- `reflection/condition_c2_playbook.json` is the actor-facing indexed representation;
- `reflection/condition_c2_feedback.jsonl` records review provenance;
- `reflection/condition_c2_outputs/` contains per-run trajectory/review/reflection artifacts.

Do not manually edit collected experiment JSONL files after collection.

Do not mix smoke runs, interrupted attempts, invalidated runs, or active continual trajectories into frozen controlled datasets.

## Documentation update rule

After a meaningful milestone or controller boundary:

1. update `CONTINUAL_C2_STATUS.md` if the active phase changed;
2. update `CONTROLLER_HISTORY.md` if a controller/version boundary changed;
3. record implementation changes in `CHANGELOG.md`;
4. add stable behavioral findings to `OBSERVATIONS.md` when appropriate;
5. record major methodological decisions in `PROJECT_LOG.md`;
6. freeze important checkpoints under `spirecomm/runs/<checkpoint_name>/`;
7. keep invalidated/debug datasets visibly separate from accepted datasets.

## Key archives

Final controlled datasets:

```text
spirecomm/runs/B2_v1_1_1_15runs_final/
spirecomm/runs/C2_v1_2_1_15runs_final/
```

Continual checkpoints:

```text
spirecomm/runs/C2_continual_v1_0_through_run28/
spirecomm/runs/C2_continual_through_run32_pre_v1_2/
```

For the complete archive map, see `spirecomm/runs/README.md`.

## Central research question

> To what extent can iterative human feedback improve the long-horizon decision-making of an LLM agent in Slay the Spire, compared with autonomous self-reflection under the same memory system?
