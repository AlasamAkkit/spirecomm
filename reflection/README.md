# Reflection and Memory Artifacts

This directory contains the external-memory and reflection artifacts used by the Slay the Spire experiments. These files are part of the research state, not model-weight training.

## Active continual-C2 state

The live continual human-teaching phase uses condition-specific files such as:

```text
condition_c2_raw_memory.jsonl
condition_c2_playbook.json
condition_c2_feedback.jsonl
condition_c2_outputs/
```

Their roles are:

- **raw memory** — permanent source lessons with provenance;
- **playbook** — actor-facing indexed rules derived from raw memory;
- **feedback bank** — one human-review record per completed C2 run;
- **condition outputs** — trajectory, initial reflection, review, and final-reflection artifacts for individual runs.

At version boundaries, verify that `playbook.updated_through_run` equals the latest completed/reflected run before starting the next controller.

## Authoritative human teaching

C2 uses `authoritative-human-teaching-v1`.

For `HUMAN_TEACHING`:

- the human strategic text is stored verbatim;
- metadata may identify title, primary category, and `applies_to`;
- the strategic content must not be paraphrased or rewritten;
- actor-facing authoritative guidance must remain textually identical to the stored teaching.

## Expert Ironclad card priors

```text
ironclad_card_priors.json
```

This is a fixed expert-quality prior used by the continual card-reward evaluator beginning with the Run-29 architecture intervention.

It is **advisory**, not an absolute card-pick table. Current deck structure, human teaching, current Act/boss, duplicates, synergy, energy, draw, defense, scaling, and Skip can override the prior.

## Historical / development artifacts

The repository intentionally retains older reflection code and smoke/development outputs because they document the evolution of the experiment.

Do not combine smoke or invalidated memory artifacts with final controlled datasets.

For final matched B2/C2 analysis, use only the frozen run archives identified in:

```text
spirecomm/docs/protocols/B2_C2_FINAL_PROTOCOL.md
```

For the active continual phase, use:

```text
spirecomm/docs/protocols/C2_CONTINUAL_TEACHING_PROTOCOL.md
spirecomm/docs/CONTINUAL_C2_STATUS.md
```

## Source-of-truth principle

A lesson's raw-memory record is the authoritative provenance record. The playbook is a retrieval/indexing representation and must preserve source coverage.

Runtime decisions and memory-retrieval evidence are recorded in the structured event log under `spirecomm/`.
