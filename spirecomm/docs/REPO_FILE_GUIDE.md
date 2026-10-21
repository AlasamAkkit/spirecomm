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

## Current active workflow (Run 39 onward)

The active, minimal run interface is now:

```text
spirecomm/test_connection.py            launcher: one obvious game entry point
spirecomm/test_connection_c2_a10.py     A10 policy override beginning Run 39
spirecomm/test_connection_c2_stable.py  preserved v1.4.0 gameplay core
spirecomm/finalize_pending_review.py    one-shot offline feedback finalizer
reflection/feedback_app.py              verbatim-teaching and question-review UI
reflection/active_review.py             optional post-run diagnostic review
reflection/followup_reflection.py        immutable human teaching + playbook
```

Historical `test_connection_c2_continual_v1*.py` modules **must remain in
place** because the active stable controller dynamically imports this
versioned ancestry by filename. Historical Run-28..36 finalization scripts
and checkpoints are research tools, not ordinary entry points; preserve them
for reproducibility rather than deleting or relocating them blindly.

For exact transition and verification instructions see
[A10_ACTIVE_REVIEW_RUN39.md](A10_ACTIVE_REVIEW_RUN39.md). The instructions
below refer to the old Run-36-to-Run-37 stable activation and are retained
as historical provenance, not as current setup steps.

## Runtime/controller files

### `spirecomm/test_connection.py`

The **active local entry point**. Historical research boundaries previously replaced it as controllers changed. Run 37 and 38 ran under locally installed **v1.4.0**. From the new Run-39 A10 cutover branch, this file is a minimal launcher importing the A10 policy wrapper, which in turn preserves the v1.4.0 gameplay core. Event metadata, not the current launcher, remains the authoritative provenance.

Do not use the current contents of this file to infer which controller produced an older run. Use the run's structured event metadata instead.

### Versioned continual controllers

```text
spirecomm/test_connection_c2_continual_v1.py
spirecomm/test_connection_c2_continual_v1_1.py
spirecomm/test_connection_c2_continual_v1_1_1.py
spirecomm/test_connection_c2_continual_v1_1_2.py
spirecomm/test_connection_c2_continual_v1_2.py
spirecomm/test_connection_c2_continual_v1_2_1.py
```

These stay at their current paths because later wrappers dynamically import earlier versions. Moving them would break historical controller imports and checkpoint reproducibility.

See `CONTROLLER_HISTORY.md` for which versions were actually used.

### Finalize-only wrappers

```text
spirecomm/test_connection_c2_finalize_run32.py
spirecomm/test_connection_c2_finalize_run33.py
```

These process a completed run's pending feedback/reflection while preventing the next gameplay run from starting under the wrong controller.

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
spirecomm/freeze_c2_run36_stable_baseline.py
spirecomm/activate_c2_stable.py
```

- Historical controllers remain at their original import paths; the stable wrapper imports v1.3.1 and its predecessor modules.
- `activate_c2_stable.py` runs once after Run-36 finalization; it compiles, freezes a local zip checkpoint, runs regression checks and then installs the stable entry point if all pass.
- `test_c2_stable_preflight.py` covers encounter transition, End-turn checks, Frail, Orichalcum and cumulative-memory coverage. At activation **10/10 passed**.
- `runs/C2_continual_through_run36_pre_stable/` is a **local** compressed stable-boundary checkpoint; do not assume it was committed to the remote branch.
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

The documentation has been reorganized around those stable runtime paths rather than moving runtime-critical code for cosmetic reasons.
