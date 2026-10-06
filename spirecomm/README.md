# spirecomm + Slay the Spire LLM FYP

This directory contains the local `spirecomm` package together with the experiment controllers used by the FYP.

The original `spirecomm` package provides Python-side communication with ForgottenArbiter's CommunicationMod. The FYP extends that base with:

- an LLM gameplay controller;
- constrained legal-action selection;
- structured experiment logging;
- watchdog and transition recovery;
- post-run reflection;
- persistent cross-run memory;
- cumulative playbook retrieval;
- human-feedback workflows;
- frozen experimental datasets and protocol documentation.

## CommunicationMod

CommunicationMod allows an external process to exchange commands and game-state JSON with Slay the Spire.

Original project:

https://github.com/ForgottenArbiter/CommunicationMod

## Active experiment entrypoint

CommunicationMod is configured to launch:

```text
spirecomm/test_connection.py
```

For reproducible experiments, a versioned controller is copied over that active filename before collection.

The completed final matched follow-up used:

- `test_connection_b2_v1_1_1.py` for the autonomous B2 control;
- `test_connection_c2_v1_2_1.py` for the authoritative human-taught C2 treatment.

The final C2 controller is currently the active `test_connection.py` snapshot.

## Final matched experiment

Both final controllers use:

- model: `gpt-5.6-luna`;
- character: Ironclad;
- Ascension: 0;
- official seeds `260925001` through `260925015` in the same order;
- the same legal-action interface;
- `cumulative-playbook-v2`;
- the Smoke Bomb transition guard;
- the permanent card-reward skip guard.

B2 performs autonomous self-reflection. C2 adds authoritative post-run human review in which the reviewer either approves the initial lessons unchanged or supplies verbatim natural-language teaching.

The final comparison is documented in:

```text
docs/FINAL_B2_C2_ANALYSIS.md
```

and the full protocol/history is in:

```text
FOLLOWUP_B2_C2_FINAL_PROTOCOL.md
```

## Frozen datasets

See:

```text
runs/README.md
```

Final datasets include the 30-run A/B/C1 studies and the 15-run final B2/C2 matched follow-up.

## Package installation

The legacy package can still be installed from this directory with:

```bash
python setup.py install
```

The FYP controller additionally requires the OpenAI Python SDK and an `OPENAI_API_KEY`.

## Documentation

Research records are maintained under `docs/`:

- `PROJECT_LOG.md`
- `EXPERIMENTS.md`
- `OBSERVATIONS.md`
- `CHANGELOG.md`
- `FINAL_B2_C2_ANALYSIS.md`
