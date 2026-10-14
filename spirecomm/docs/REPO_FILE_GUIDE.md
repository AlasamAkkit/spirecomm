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

## Runtime/controller files

### `spirecomm/test_connection.py`

The **active local entry point**. This file is intentionally replaced when the experiment switches controller versions.

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
