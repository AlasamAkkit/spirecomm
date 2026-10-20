# spirecomm + Slay the Spire LLM FYP

This directory contains the local `spirecomm` package together with the runtime controllers, logs, checkpoints, and research documentation used by the FYP.

The original `spirecomm` package provides Python-side communication with ForgottenArbiter's CommunicationMod. The FYP extends that base with:

- LLM gameplay control;
- constrained legal-action selection;
- structured experiment logging;
- watchdog and transition recovery;
- post-run reflection;
- persistent cross-run memory;
- cumulative/focused playbook retrieval;
- authoritative human-teaching workflows;
- persistent deck planning;
- sticky within-turn combat planning;
- frozen datasets and longitudinal checkpoints.

## Active entry point and stable workflow

CommunicationMod launches `spirecomm/test_connection.py`. On the user's laptop, the one-time `activate_c2_stable.py` check installed the fixed **v1.4.0** controller after validating the finalized Run-36 checkpoint and passing all ten regression tests. The GitHub copy of `test_connection.py` is not necessarily the deployed local copy.

**Do not copy new versions after each run.** For Runs 37+, allow each completed run to generate a reflection, then finalize `APPROVE_INITIAL` or `HUMAN_TEACHING` using the feedback app. The playbook updates before another run can start. Run 37 was reported in progress; no outcome is asserted yet.

Baseline at activation: **36 completed/reflected runs, 50 raw lessons, 36 rules, Ascension 0**.

See [Stable feedback workflow](docs/C2_STABLE_FEEDBACK_WORKFLOW.md), [System architecture/retrospective](docs/SYSTEM_ARCHITECTURE_AND_RETROSPECTIVE.md), and [Current status](docs/CONTINUAL_C2_STATUS.md). Always attribute historical runs to their logged `continual_controller_version`, not the present contents of `test_connection.py`.

## Controller history

Important continual controller files remain in this directory because later versions dynamically import earlier ones.

```text
test_connection_c2_continual_v1.py
test_connection_c2_continual_v1_1.py
test_connection_c2_continual_v1_1_1.py
test_connection_c2_continual_v1_1_2.py
test_connection_c2_continual_v1_2.py
test_connection_c2_continual_v1_2_1.py
test_connection_c2_continual_v1_3.py
test_connection_c2_continual_v1_3_1.py
test_connection_c2_stable.py
```

They are intentionally **not moved into a cosmetic subdirectory**, because doing so would break historical import paths and reduce reproducibility.

`test_connection_c2_continual_v1_1_2.py` was developed but not used as a completed-run experimental phase.

## Final matched experiment

The controlled B2/C2 experiment is complete and frozen.

Final controllers:

- `test_connection_b2_v1_1_1.py` — autonomous B2 control;
- `test_connection_c2_v1_2_1.py` — authoritative human-taught C2 treatment.

Headline result:

| Metric | B2 | C2 |
|---|---:|---:|
| Mean floor | 18.73 | **27.33** |
| Median floor | 16 | **23** |
| Mean score | 144.60 | **251.47** |
| Act 2+ | 6/15 | **13/15** |
| Act 3 | 0/15 | **2/15** |
| Wins | 0 | 0 |

Canonical controlled protocol:

```text
docs/protocols/B2_C2_FINAL_PROTOCOL.md
```

Final analysis:

```text
docs/FINAL_B2_C2_ANALYSIS.md
```

## Logs and checkpoints

Active continual structured log:

```text
run_events_c2.jsonl
```

Supporting logs can include:

```text
agent_debug_c2.log
sts_messages_c2.log
state_dumps_c2.jsonl
```

Important continual checkpoints:

```text
runs/C2_continual_v1_0_through_run28/
runs/C2_continual_through_run32_pre_v1_2/
```

See `runs/README.md` for the complete archive guide.

## Safe controller transitions

A `RUN_END` can exist before the run's feedback/reflection pipeline is complete.

At a controller-version boundary, verify:

```text
POST_RUN_REFLECTION_COMPLETE == latest completed run
playbook updated_through_run == latest completed run
```

Finalize-only wrappers currently include:

```text
test_connection_c2_finalize_run32.py
test_connection_c2_finalize_run33.py
```

They allow pending feedback/reflection to complete while preventing the next gameplay run from starting under the old controller.

## CommunicationMod

CommunicationMod allows an external process to exchange commands and game-state JSON with Slay the Spire.

Original project:

```text
https://github.com/ForgottenArbiter/CommunicationMod
```

## Package installation

The legacy package can still be installed from this directory with:

```bash
python setup.py install
```

The FYP controller additionally requires the OpenAI Python SDK and an `OPENAI_API_KEY`.

## Documentation

Start at:

```text
docs/README.md
```

Key references:

- `docs/EXPERIMENTS.md`
- `docs/PROJECT_LOG.md`
- `docs/CONTINUAL_C2_STATUS.md`
- `docs/CONTROLLER_HISTORY.md`
- `docs/LEARNING_PIPELINE.md`
- `docs/HUMAN_FEEDBACK_MECHANISM.md`
- `docs/LOGGING_SCHEMA.md`
- `docs/REPO_FILE_GUIDE.md`
