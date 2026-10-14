# M1.4 Reflection Pipeline — Historical Milestone

> **Status:** HISTORICAL. This file records the earlier reflection/memory milestone that led to Conditions B/C1 and later B2/C2. It is not the active continual-C2 protocol.

## Milestone objective

Build a reproducible post-run pipeline that can turn a completed Slay the Spire trajectory into reusable cross-run lessons without updating model weights.

The milestone established the basic pattern:

```text
completed run
 -> compact trajectory
 -> reflection-v0.2
 -> structured reusable lessons
 -> persistent external memory
 -> later decision-time retrieval
```

## Reflection-v0.2 design goals

The reflector was required to:

- generate at most a small number of reusable lessons;
- cite concrete trajectory evidence;
- prefer causal/strategic explanations over merely describing the death screen;
- distinguish temporary/generated combat card choices from permanent deck additions;
- avoid unsupported map/topology claims;
- avoid using information that was not available at the relevant decision time.

## What the milestone demonstrated

Offline validation on completed trajectories showed that the reflection system could identify useful recurring patterns, but it also exposed an important research limitation:

> A structurally valid LLM reflection can still be strategically wrong.

Typical failure modes included:

- incorrect causal attribution;
- overly broad lessons from one trajectory;
- vague advice without a decision condition;
- duplicated lessons;
- false confidence about route/deck context.

Those errors were intentionally left uncorrected in autonomous Condition B.

## How it evolved

### Condition B

Reflection-v0.2 lessons were stored automatically and retrieved by exact category, newest first, maximum three.

### Condition C1

The same reflection interface was retained, but a human reviewed lessons before storage.

### B2/C2

The rolling newest-three memory system was replaced by permanent raw memory plus `cumulative-playbook-v2` with cross-category `applies_to` scopes and source-ID coverage validation.

### Final C2

Human teaching became authoritative and verbatim rather than being rewritten by another strategic LLM.

### Continual C2

The reflection/memory pipeline remains, but decision-time execution has evolved further with persistent deck plans, sticky combat plans, and focused memory retrieval.

## Current references

Use these files for the current system:

- `LEARNING_PIPELINE.md`
- `HUMAN_FEEDBACK_MECHANISM.md`
- `protocols/B2_C2_FINAL_PROTOCOL.md`
- `protocols/C2_CONTINUAL_TEACHING_PROTOCOL.md`
- `CONTINUAL_C2_STATUS.md`

This milestone file is retained to explain how the current external-memory design developed from the original reflection experiment.
