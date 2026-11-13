# FYP Research Documentation

This directory is the canonical documentation hub for the Slay the Spire LLM self-reflection / human-teaching FYP.

The documentation is split into **frozen controlled-phase records**, **active continual-phase records**, and **engineering/reference documents** so later controller changes do not overwrite the interpretation of earlier experiments.

## Start here

- [System architecture and issue retrospective](SYSTEM_ARCHITECTURE_AND_RETROSPECTIVE.md) — complete end-to-end explanation and engineering fixes.
- [Offline learning audit (read-only)](CONTINUAL_LEARNING_AUDIT.md) — test cumulative-memory coverage, repetition and attention without changing v1.6.1.
- [Run-49 active controller guide](RUN49_CONTROLLER_V161.md) — current v1.6.1 setup, checkpoint and tests.
- [Run-48 v1.6.0 historical guide](RUN48_CONTROLLER_V16.md) — first live v1.6.0 intervention, no longer the active launcher.
- [A10 Run-39 historical guide](A10_ACTIVE_REVIEW_RUN39.md) — earlier A10 activation, not the current launcher.
- [Stable feedback instructions](C2_STABLE_FEEDBACK_WORKFLOW.md) — historical Run-37 activation and earlier teaching loop.
- [Runs 33–37 ledger](CONTINUAL_RUN_LEDGER_33_37.md) — verified historical outcomes and checkpoint counts.

### Current project status

- [`CONTINUAL_C2_STATUS.md`](CONTINUAL_C2_STATUS.md) — live longitudinal status through the latest reviewer-confirmed run (Run 48) and pending local checkpoint.
- [`CONTROLLER_HISTORY.md`](CONTROLLER_HISTORY.md) — exact mapping from run ranges to controller versions and intervention boundaries.
- [`PROJECT_LOG.md`](PROJECT_LOG.md) — chronological milestones, with Run-48/49 versioned addenda.

### Protocols

Canonical protocols live in [`protocols/`](protocols/):

- [`protocols/B2_C2_FINAL_PROTOCOL.md`](protocols/B2_C2_FINAL_PROTOCOL.md) — completed/frozen matched B2/C2 experiment.
- [`protocols/C2_CONTINUAL_TEACHING_PROTOCOL.md`](protocols/C2_CONTINUAL_TEACHING_PROTOCOL.md) — active open-ended continual-C2 protocol.
- [`protocols/README.md`](protocols/README.md) — protocol index and compatibility-path notes.

The old root-level protocol filenames are retained only as compatibility pointers.

### Experiment records

- [`EXPERIMENTS.md`](EXPERIMENTS.md) — canonical ledger covering Phase I, matched Phase II, and separate continual phases.
- [`RUNS_39_48_A10_EVALUATION.md`](RUNS_39_48_A10_EVALUATION.md) — outcomes and research cautions for Runs 37–48 and the Run-49 code boundary.
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

### Continual C2 — A10 stress-test phase

- Runs 16–36: historical exploratory controller interventions.
- Run 37: first A0 victory, score 707, Act 3 Floor 51.
- Run 38: A1 loss, score 184, Act 2 Floor 21; the user confirmed
  feedback ingestion locally (playbook updated through Run 38).
- Runs 39–42: A10 stress-test runs using the v1.4 controller; Run 42 is
  reported finalized with the local playbook updated through Run 42.
- Runs 43–47: A10 v1.5, with explicit Neow human-teaching supersession and conservative verifier checks. Run 47 was reported finalized.
- Run 48 v1.6.0; Run 49 onward v1.6.1: v1.6 code and offline tests committed; target identity, action feasibility and verifier attribution added. **Run 48 live gameplay is unverified.**
- Historical v1.4 and v1.5 gameplay controllers are preserved; optional
  post-run diagnostic questions extend the authoritative human teaching UI.
- v1.6 source and feedback-attribution changes are committed to `master` and GitHub offline checks passed. The current launcher imports `test_connection_c2_run48.py`.

**Current operational guide:** [RUN48_CONTROLLER_V16.md](RUN48_CONTROLLER_V16.md).
Prior v1.5: [RUN43_ACTIVE_SUPERSESSION.md](RUN43_ACTIVE_SUPERSESSION.md).
Earlier A10 activation: [A10_ACTIVE_REVIEW_RUN39.md](A10_ACTIVE_REVIEW_RUN39.md).

The older Run-37 stable activation notes and Run-36 checkpoint are historical.
Keep all run-specific records, controller versions, and experimental boundaries
for reproducibility. The local `reflection/condition_c2_playbook.json` and
`spirecomm/run_events_c2.jsonl` are the current state, while the tracked
`C2_through_run38_pre_A10` archive intentionally captures the *pre-final*
Run-38 state; the finalized Run-47 evidence and write-once pre-v1.6 checkpoint must be validated locally.

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
