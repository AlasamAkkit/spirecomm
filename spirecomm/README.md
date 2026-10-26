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

CommunicationMod launches `spirecomm/test_connection.py`, intentionally a
**small controller launcher**. From Run 43 it imports `test_connection_c2_run43.py`,
which adds a scoped human correction and conservative verifier gates to
`test_connection_c2_a10.py`. The latter extends
the preserved `test_connection_c2_stable.py` v1.4 gameplay controller. That
controller dynamically imports versioned v1.0–v1.3.1 modules; therefore the
historical controller files still belong in the root.

The Run-37 stable activation was completed with the historical
`archive/legacy_tools/activate_c2_stable.py` utility. Run 37 achieved the
first A0 win; Run 38 was an A1 loss, and the user reported its feedback was
ingested into the cumulative playbook through Run 38. Runs 39–42 executed at **Ascension 10**; Run 42 was reported finalized locally.
Run 43 is the first scheduled v1.5 active-policy intervention.

For normal ongoing use, **do not run historical activators or freeze tools**.
Use `reflection/feedback_app.py` for authoritative verbatim teaching and
optional evidence-linked corrections, and
`spirecomm/finalize_pending_review.py` only when offline recovery is needed.

See [Run-43 controller cutover](docs/RUN43_ACTIVE_SUPERSESSION.md),
[A10 historical setup](docs/A10_ACTIVE_REVIEW_RUN39.md),
[Repository file guide](docs/REPO_FILE_GUIDE.md) and
[System architecture](docs/SYSTEM_ARCHITECTURE_AND_RETROSPECTIVE.md).
Historical runs must always be attributed using event metadata, not the
present version of `test_connection.py`.

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

Historical finalize-only wrappers have moved into `archive/legacy_tools/`.
Use `finalize_pending_review.py` for the current offline recovery workflow.

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


## Archived one-time scripts

The completed experiment phases generated many `freeze_c2_runXX` and
`test_connection_c2_finalize_runXX` scripts. They have been grouped under
[`archive/legacy_tools/`](archive/legacy_tools/README.md), alongside the
old Run-36 activation and Run-15 preparation scripts. Their historical
controller dependencies were **not** moved, because the active v1.4
controller imports that versioned chain.

The ~10-line `test_connection.py` is only the launcher; the gameplay and
memory code still exists in the imported modules.
