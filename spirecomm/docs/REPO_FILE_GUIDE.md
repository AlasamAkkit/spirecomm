# Repository File Guide

This guide explains which files are active runtime state, frozen research artifacts, historical controllers, or documentation.

## Top level

```text
README.md
reflection/
spirecomm/
```

- `README.md` — high-level project summary and current status.
- `reflection/` — external memory, feedback, reflection outputs, and fixed card priors.
- `spirecomm/` — Python package, active controller entry point, historical controller versions, structured logs, checkpoints, and research docs.

## Current active workflow (Run 49 onward)

The active, minimal run interface is now:

```text
spirecomm/test_connection.py            launcher: one obvious game entry point
spirecomm/test_connection_c2_run49.py   v1.6.1 controller for planned Run 49
spirecomm/run49_policy.py               equivalent-card and X-cost guards
spirecomm/freeze_c2_run48_checkpoint.py one-time Run-48 local checkpoint
spirecomm/test_c2_run49_preflight.py     synthetic Run-49 regression suite
spirecomm/test_connection_c2_run48.py   historical v1.6.0 controller (Run 48)
spirecomm/run48_policy.py               target/legality/intent checks
spirecomm/test_connection_c2_run43.py   inherited v1.5 Neow correction
spirecomm/run43_policy.py               inherited v1.5 safeguards
spirecomm/test_connection_c2_a10.py     fixed A10 policy beginning Run 39
spirecomm/test_connection_c2_stable.py  preserved v1.4.0 gameplay core
spirecomm/freeze_c2_run47_checkpoint.py one-time local Run-47 checkpoint
spirecomm/test_c2_run48_preflight.py     synthetic v1.6 tests
spirecomm/finalize_pending_review.py    one-shot offline feedback finalizer
reflection/feedback_app.py              verbatim-teaching and question-review UI
reflection/active_review.py             optional post-run diagnostic review
reflection/followup_reflection.py        immutable human teaching + playbook
```

Historical `test_connection_c2_continual_v1*.py` modules **must remain in
place** because the active stable controller dynamically imports this
versioned ancestry by filename. Historical Run-28..36 finalizers, checkpoint/freezer helpers, and one-time
activation scripts now live under `spirecomm/archive/legacy_tools/`. Their
original controller dependencies still live in the project root so the
active runtime remains unchanged. See the archive README for provenance.

For exact transition and verification instructions see
[RUN49_CONTROLLER_V161.md](RUN49_CONTROLLER_V161.md); the prior [Run-39 A10 activation](A10_ACTIVE_REVIEW_RUN39.md) is historical. The instructions
below refer to the old Run-36-to-Run-37 stable activation and are retained
as historical provenance, not as current setup steps.

## Runtime/controller files

### `spirecomm/test_connection.py`

The **active local entry point**: a short launcher importing `test_connection_c2_run49.py` (v1.6.1), which inherits the v1.5 human correction, v1.4 stable gameplay and fixed A10 scheduling. Runs 37–42, 43–47 and 48+ have distinct versioned boundaries. Event metadata, not the current launcher, remains the authoritative provenance.

Do not use the current contents of this file to infer which controller produced an older run. Use the run's structured event metadata instead.

### Versioned continual controllers

```text
spirecomm/test_connection_c2_continual_v1.py
spirecomm/test_connection_c2_continual_v1_1.py
spirecomm/test_connection_c2_continual_v1_1_1.py
spirecomm/test_connection_c2_continual_v1_1_2.py
spirecomm/test_connection_c2_continual_v1_2.py
spirecomm/test_connection_c2_continual_v1_2_1.py
spirecomm/test_connection_c2_continual_v1_3.py
spirecomm/test_connection_c2_continual_v1_3_1.py
spirecomm/test_connection_c2_stable.py
spirecomm/test_connection_c2_a10.py
spirecomm/test_connection_c2_run43.py
spirecomm/test_connection_c2_run48.py
test_connection_c2_run49.py
```

These stay at their current paths because later wrappers dynamically import earlier versions. Moving them would break historical controller imports and checkpoint reproducibility.

See `CONTROLLER_HISTORY.md` for which versions were actually used.

### Historical scripts (archived, not used for Run 48)

```text
spirecomm/archive/legacy_tools/
  test_connection_c2_finalize_run28.py ... run36.py
  freeze_c2_run28_checkpoint.py ... run36_stable_baseline.py
  activate_c2_stable.py
  prepare_c2_continual.py
```

The six one-time finalization wrappers and six checkpoint scripts have been
relocated, along with historical activation/preparation utilities. Their
path constants were adjusted to continue referring to the repository's
original runtime files and snapshot locations. They are **not** the active
Run-48 finalizer. Use `spirecomm/finalize_pending_review.py` instead for
the newer reviewed-run recovery workflow.

### Continual progress state

```text
spirecomm/c2_continual_seed_schedule.json
spirecomm/c2_continual_progress.json
```

- seed schedule persists fresh unique continual seeds across restarts;
- progress state tracks Ascension progression and processed runs.

### Stable Run-37+ controller, activation and tests

```text
spirecomm/test_connection_c2_continual_v1_3.py
spirecomm/test_connection_c2_continual_v1_3_1.py
spirecomm/test_connection_c2_stable.py
spirecomm/test_c2_v131_block_projection.py
spirecomm/test_c2_stable_preflight.py
spirecomm/archive/legacy_tools/freeze_c2_run36_stable_baseline.py
spirecomm/archive/legacy_tools/activate_c2_stable.py
```

- Historical controllers remain at their original import paths; the stable wrapper imports v1.3.1 and its predecessor modules.
- `archive/legacy_tools/activate_c2_stable.py` was used once after Run-36 finalization to install the v1.4 stable entry point. **Do not rerun it** after the A10 upgrade, as it would replace the current A10 launcher.
- `test_c2_stable_preflight.py` covers encounter transition, End-turn checks, Frail, Orichalcum and cumulative-memory coverage. At activation **10/10 passed**.
- `runs/C2_continual_through_run36_pre_stable/` holds the compressed historical stable-boundary checkpoint; it has already been committed to the repository.
- From Run 37, human feedback updates *data* (`raw_memory`, `playbook`, `feedback`, outputs), not the controller source.

## Runtime logs

Important live files include:

```text
spirecomm/run_events_c2.jsonl
spirecomm/agent_debug_c2.log
spirecomm/sts_messages_c2.log
spirecomm/state_dumps_c2.jsonl
```

`run_events_c2.jsonl` is the primary structured runtime source of truth.

Compact/debug/state logs support diagnosis but should not override the structured event record when the two differ in interpretation.

## Reflection and memory

Active C2 research state lives under `reflection/`:

```text
condition_c2_raw_memory.jsonl
condition_c2_playbook.json
condition_c2_feedback.jsonl
condition_c2_outputs/
ironclad_card_priors.json
```

See `../../reflection/README.md` for details.

## Frozen run archives

```text
spirecomm/runs/
```

Categories:

1. **final controlled datasets** — canonical performance-analysis sources;
2. **continual checkpoints** — frozen longitudinal state at architecture boundaries;
3. **invalidated/interrupted batches** — kept for provenance only;
4. **smoke/development runs** — infrastructure validation only.

See `../runs/README.md` for the archive map.

## Documentation

Canonical current docs:

```text
spirecomm/docs/README.md
spirecomm/docs/CONTINUAL_C2_STATUS.md
spirecomm/docs/CONTROLLER_HISTORY.md
spirecomm/docs/PROJECT_LOG.md
spirecomm/docs/EXPERIMENTS.md
spirecomm/docs/FINAL_B2_C2_ANALYSIS.md
spirecomm/docs/protocols/
```

Engineering/reference docs:

```text
spirecomm/docs/LEARNING_PIPELINE.md
spirecomm/docs/HUMAN_FEEDBACK_MECHANISM.md
spirecomm/docs/LOGGING_SCHEMA.md
```

Historical logs:

```text
spirecomm/docs/OBSERVATIONS.md
spirecomm/docs/CHANGELOG.md
spirecomm/docs/M1_4_REFLECTION_PIPELINE.md
```

## Protocol compatibility stubs

These root-level files remain only so old links do not break:

```text
spirecomm/FOLLOWUP_B2_C2_FINAL_PROTOCOL.md
spirecomm/PHASE3_C2_CONTINUATION_PROTOCOL.md
```

Their canonical replacements are in `spirecomm/docs/protocols/`.

## What should not be moved casually

Do not move or rename without updating every dynamic import/reference:

- versioned continual controller scripts;
- frozen controller snapshots inside run archives;
- active memory/playbook files expected by controller constants;
- live event/log paths;
- seed/progress state files.

Only one-time historical helpers were moved; the active and import-bound
controller modules remain in the same place. This keeps the visible project
root smaller without rewriting the frozen decision architecture.

**Run-48 checkpoint:** `spirecomm/runs/_local_checkpoints/C2_through_run47_pre_v1_6.zip` is local/gitignored, created after Run-47 finalization on the game machine. GitHub contains the script but does not establish that this archive exists locally.

**New Run-49 boundary:** Run 48 feedback and playbook must be finalized locally, then `freeze_c2_run48_checkpoint.py` creates the write-once pre-v1.6.1 archive. See [Run 49](RUN49_CONTROLLER_V161.md). This GitHub repository does not include the private local checkpoint.
