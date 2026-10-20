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

## Stable feedback evaluation after Run 36

The local stable activation reported:

```text
Completed and reflected C2 runs: 36
Raw lessons in condition_c2_raw_memory.jsonl: 50
Rules in condition_c2_playbook.json: 36
Feedback records: 36
Playbook updated through: 36
```

Run 37 was reported running under `c2-continual-teaching-v1.4.0-stable-feedback-loop` when this documentation was updated. Do not claim completion or modify live memory to pre-fill Run 37.

### Normal repeatable workflow

1. Allow one run to finish and produce `run_XX_trajectory_v2.txt` and `run_XX_initial_reflection.json`.
2. Review in the feedback app: `python reflection/feedback_app.py --output-dir reflection/condition_c2_outputs`.
3. Choose `APPROVE_INITIAL` or `HUMAN_TEACHING`; authoritative human wording remains verbatim.
4. Finalize and confirm `POST_RUN_REFLECTION_COMPLETE` and `condition_c2_playbook.json.updated_through_run == XX`.
5. Continue the **same** controller for the next run; no copying/changing Python controllers between ordinary feedback rounds.

**Do not manually append memories or rewrite feedback JSONL** to make counts match. If a review or memory update fails, recover it through the controller/feedback process. Preserve original run artifacts and controller-version provenance.

### Cumulative rule availability

For all-combat/permanent-card-reward prompts after Run 34, v1.3+ retrieves **all applicable** rules with `memory_top_k=null` and `omitted_memory_count=0`, while the playbook preserves raw memory source coverage. State-matched human rules may be additionally pinned. This proves exposure to past teaching; whether the chosen action followed that teaching must be tested separately in `spirecomm/run_events_c2.jsonl`.

See [stable workflow](../spirecomm/docs/C2_STABLE_FEEDBACK_WORKFLOW.md), [learning pipeline](../spirecomm/docs/LEARNING_PIPELINE.md), and [full retrospective](../spirecomm/docs/SYSTEM_ARCHITECTURE_AND_RETROSPECTIVE.md).
