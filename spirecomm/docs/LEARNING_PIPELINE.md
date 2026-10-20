# Learning Pipeline

The project does not train model weights. Learning is implemented as persistent **external memory** plus decision-time retrieval.

## 1. End-to-end flow

```text
Slay the Spire run
 -> structured event log
 -> compact trajectory
 -> initial LLM reflection
 -> condition-specific finalization
 -> permanent raw memory
 -> cumulative playbook
 -> later decision-time retrieval
```

For continual C2, two additional runtime state layers now exist:

```text
persistent run-level deck plan
sticky within-turn combat plan
```

These are decision-state mechanisms, not permanent cross-run memory.

## 2. Controlled B2 path

```text
completed run
 -> trajectory
 -> autonomous LLM reflection
 -> final lessons
 -> raw memory
 -> cumulative-playbook-v2
 -> later actor prompts
```

No human semantic correction is permitted.

## 3. Controlled/continual C2 path

```text
completed run
 -> trajectory
 -> initial LLM reflection
 -> human review
      -> APPROVE_INITIAL
      OR
      -> HUMAN_TEACHING
 -> final lessons
 -> raw memory
 -> cumulative playbook
 -> later actor prompts
```

### `APPROVE_INITIAL`

The initial reflection lessons are stored unchanged.

### `HUMAN_TEACHING`

The human's natural-language strategic teaching is stored verbatim. An LLM may infer retrieval metadata only.

## 4. Raw memory

The raw-memory record is the provenance source of truth for learned lessons.

Typical fields include:

```text
id
source / condition
source_run
source_run_id
category
title
lesson
confidence
applies_to
authoritative
human_feedback_verbatim
```

The exact schema can evolve, but source/run provenance and authoritative text must remain auditable.

## 5. Cumulative playbook

The playbook indexes raw lessons for decision-time retrieval.

Rules can contain:

```text
rule_id
category
applies_to
when
guidance
rationale
confidence
source_memory_ids
authoritative
```

Validation requires every retained raw-memory ID to remain represented by at least one playbook rule.

For authoritative human teaching, actor-facing guidance must preserve the original human text exactly.

## 6. Retrieval evolution

### Original B/C1

```text
exact category
newest first
max 3
```

Limitations:

- useful older lessons aged out;
- cross-category guidance could be hidden by a single primary category.

### B2/C2 matched experiment

`cumulative-playbook-v2` supplied all rules whose `applies_to` included the current category.

This fixed rolling-window loss but eventually created large tactical prompts during the continual phase as authoritative memory accumulated.

### Continual v1.2 focused retrieval

High-frequency decisions now use bounded focused subsets:

```text
COMBAT      -> max 8 rules
CARD_REWARD -> max 10 rules
```

All raw memory remains stored; the limit applies only to the actor prompt.

### v1.2.1 ranking hotfix

Run 33 showed that v1.2.0 could rank old exact-primary-category rules above a newer cross-category authoritative lesson even though the newer lesson's `applies_to` included the current category.

Run 34+ ranking:

```text
applicability filter
 -> authoritative status
 -> source-run recency
 -> primary-category tie-break
 -> GENERAL tie-break
```

Policy:

```text
focused_authority_applicability_recent_v1
```

### v1.3 cumulative all-applicable retrieval (Run 35 onward)

Run 34 proved a correct focused ranking could still exclude **older** authoritative lessons from the actor prompt, despite their survival in raw memory and the playbook. From Run 35, retrieval returns **all rules whose `applies_to` matches the decision** (including GENERAL), without a top-k cutoff. `memory_top_k=null` and `omitted_memory_count=0` are logged. Relevant human teaching can be pinned at the top when a current enemy/card/relic name occurs in the original human guidance. Cumulative coverage is checked by source-memory ID.

This is deliberately different from the historical Run-33/34 focused retrieval; do not describe the focused top-k rule as the current stable policy. Availability and verbatim preservation do not guarantee a model will follow every lesson.

### v1.3.1 known Block simulation and v1.4 stable safeguards

Run 36 added explicit effective Block projections for supported cards, applying Dexterity followed by Frail and per-card rounding. It is an *auditable estimate*, not a complete simulator.

Run 37+ freezes the controller and adds: encounter-scoped sticky plan invalidation, queued End-turn re-verification, and a bounded override when a known attacking intent would cause preventable unblocked HP damage and an effective legal Block card is available. The special end-turn relic Orichalcum is considered to avoid overriding better free block.

All other game decisions still rely on the LLM and existing constrained legal actions. This distinction matters for the FYP: **fixed execution safeguards are code; learning is the persistent human-feedback/playbook pipeline**.

## 7. Persistent deck plan

Beginning with Run 33, permanent card rewards maintain a run-level plan containing:

- offense;
- defense;
- scaling;
- draw/energy;
- AoE;
- weaknesses;
- acquisition priorities;
- avoid list;
- add policy.

The card evaluator must score every offered card plus Skip against this plan.

The model returns final desirability scores, and the controller deterministically selects the maximum score. Skip wins exact ties.

The plan may evolve during the run, but a change should be justified rather than silently drifting from one reward to the next.

## 8. Sticky combat planning

Run 29–32 turn planning generated a full-turn proposal but executed only the first action before replanning from scratch. Run 32 showed that the fresh plan could contradict the original defensive sequence.

Run 33+ stores the remaining semantic actions from the plan.

```text
create ordered sequence
 -> execute first action
 -> if next planned action remains valid, follow it
 -> continue until sequence ends
 -> replan when plan is invalidated or intentionally stopped by a state-changing action
```

Important events:

```text
STICKY_COMBAT_PLAN_CREATED
STICKY_COMBAT_PLAN_FOLLOWED
STICKY_COMBAT_PLAN_INVALIDATED
```

Draw-changing actions can intentionally create a one-action sequence so the controller replans after seeing the new hand.

## 9. Finalization boundary

A gameplay run is not fully incorporated into memory at `RUN_END` alone.

A safe completed learning cycle requires:

```text
RUN_END
human review finalized
final reflection written
raw memory/playbook updated
POST_RUN_REFLECTION_COMPLETE
```

Before a controller-version change, use a finalize-only wrapper when necessary so the pending reflection can complete without the next gameplay run starting under the old controller.

## 10. Research interpretation

Controlled B2/C2 isolates the presence of authoritative human teaching under the same cumulative-memory architecture.

Runs 16–36 explored how teaching and execution architecture interact over time, with explicitly recorded interventions. Runs 37+ instead hold the v1.4.0 controller constant to study accumulated human teaching in a more stable longitudinal setting (still across independent seeds). See SYSTEM_ARCHITECTURE_AND_RETROSPECTIVE.md.
