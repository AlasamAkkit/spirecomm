# FYP Research Documentation

This directory is the canonical documentation hub for the Slay the Spire LLM self-reflection / human-teaching FYP.

The documentation is split into **frozen controlled-phase records**, **active continual-phase records**, and **engineering/reference documents** so later controller changes do not overwrite the interpretation of earlier experiments.

## Start here

- [System architecture and issue retrospective](SYSTEM_ARCHITECTURE_AND_RETROSPECTIVE.md) — complete end-to-end explanation and engineering fixes.
- [Stable feedback instructions](C2_STABLE_FEEDBACK_WORKFLOW.md) — one-time activation and repeated teaching loop.
- [Runs 33–37 ledger](CONTINUAL_RUN_LEDGER_33_37.md) — verified historical outcomes and checkpoint counts.

### Current project status

- [`CONTINUAL_C2_STATUS.md`](CONTINUAL_C2_STATUS.md) — live longitudinal status through the latest finalized checkpoint.
- [`CONTROLLER_HISTORY.md`](CONTROLLER_HISTORY.md) — exact mapping from run ranges to controller versions and intervention boundaries.
- [`PROJECT_LOG.md`](PROJECT_LOG.md) — chronological research/architecture milestones through the stable Run-37 boundary.

### Protocols

Canonical protocols live in [`protocols/`](protocols/):

- [`protocols/B2_C2_FINAL_PROTOCOL.md`](protocols/B2_C2_FINAL_PROTOCOL.md) — completed/frozen matched B2/C2 experiment.
- [`protocols/C2_CONTINUAL_TEACHING_PROTOCOL.md`](protocols/C2_CONTINUAL_TEACHING_PROTOCOL.md) — active open-ended continual-C2 protocol.
- [`protocols/README.md`](protocols/README.md) — protocol index and compatibility-path notes.

The old root-level protocol filenames are retained only as compatibility pointers.

### Experiment records

- [`EXPERIMENTS.md`](EXPERIMENTS.md) — canonical ledger covering Phase I, matched Phase II, and the separate continual phase.
- [`FINAL_B2_C2_ANALYSIS.md`](FINAL_B2_C2_ANALYSIS.md) — **frozen** final matched B2/C2 comparison, integrity summary, interpretation, and limitations.

### Engineering / learning-system reference

- [`LEARNING_PIPELINE.md`](LEARNING_PIPELINE.md) — reflection, review, raw memory, playbook, retrieval, persistent deck planning, and sticky combat planning.
- [`HUMAN_FEEDBACK_MECHANISM.md`](HUMAN_FEEDBACK_MECHANISM.md) — authoritative human-teaching semantics and review workflow.
- [`LOGGING_SCHEMA.md`](LOGGING_SCHEMA.md) — current structured logging/event reference.
- [`REPO_FILE_GUIDE.md`](REPO_FILE_GUIDE.md) — repository layout and source-of-truth guide.
- [`M1_4_REFLECTION_PIPELINE.md`](M1_4_REFLECTION_PIPELINE.md) — restored historical reflection-pipeline milestone note.

### Historical and continual change/observation logs

- [`OBSERVATIONS.md`](OBSERVATIONS.md) — original stable observation record through OBS-088.
- [`CONTINUAL_OBSERVATIONS.md`](CONTINUAL_OBSERVATIONS.md) — continuation from OBS-089 onward.
- [`CHANGELOG.md`](CHANGELOG.md) — earlier controller/reflection/experiment infrastructure history.
- [`CONTINUAL_CHANGELOG.md`](CONTINUAL_CHANGELOG.md) — post-controlled continual-C2 implementation history.

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

### Continual C2 — fixed-controller evaluation

Finalized and reflected through **Run 36**: **50 raw lessons, 36 playbook rules, 36 feedback records**, Ascension 0. The user reported **Run 37 in progress** under the **v1.4.0 stable-feedback-loop controller** after a one-time activation and 10/10 regression-test pass. A Run-37 result is **not yet recorded here**.

```text
Runs 16–28  original continual v1.0
Runs 29–32  v1.1.1 card priors / replan-every-action
Run 33      v1.2.0 persistent deck and sticky combat planning
Run 34      v1.2.1 focused-memory ranking hotfix
Run 35      v1.3.0 full cumulative retrieval + verifier
Run 36      v1.3.1 known Block/Frail/Dexterity projection
Run 37+     v1.4.0 stable controller (fixed for feedback evaluation)
```

Runs 16–36 are **exploratory engineering/teaching** with explicit intervention boundaries. For Runs 37+, hold the implementation fixed to study accumulated human teaching; do not treat ordinary losses as a reason for a new controller.

Key new references:

- [SYSTEM_ARCHITECTURE_AND_RETROSPECTIVE.md](SYSTEM_ARCHITECTURE_AND_RETROSPECTIVE.md)
- [CONTINUAL_RUN_LEDGER_33_37.md](CONTINUAL_RUN_LEDGER_33_37.md)
- [C2_STABLE_FEEDBACK_WORKFLOW.md](C2_STABLE_FEEDBACK_WORKFLOW.md)

## Source-of-truth rules

For frozen experiments, the machine-readable structured event log stored with archived artifacts under `spirecomm/runs/` is the runtime source of truth.

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
3. record continual implementation changes in `CONTINUAL_CHANGELOG.md`;
4. add stable continual findings to `CONTINUAL_OBSERVATIONS.md`;
5. update `EXPERIMENTS.md` or `PROJECT_LOG.md` for major methodological milestones;
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
