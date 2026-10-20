# Human Feedback Mechanism

This document describes how human review enters the C2 learning system.

## 1. Goal

The treatment is intended to represent **direct human strategic teaching**, not human feedback rewritten by a second strategic model.

Final C2 therefore uses:

```text
authoritative-human-teaching-v1
```

## 2. Review timing

Human review happens after a completed run and after the initial autonomous reflection is available.

```text
RUN_END
 -> compact trajectory
 -> initial LLM reflection
 -> human review
 -> final lesson set
 -> raw memory / playbook update
 -> POST_RUN_REFLECTION_COMPLETE
```

The next run should not start before the previous run has completed this pipeline.

## 3. Review outcomes

### `APPROVE_INITIAL`

Use when the initial autonomous reflection is sufficiently accurate and useful.

The initial lessons are stored unchanged.

### `HUMAN_TEACHING`

Use when the human wants to replace the initial strategic lesson set with direct natural-language instruction.

The strategic text is stored verbatim.

## 4. Metadata-only processing

For `HUMAN_TEACHING`, an LLM may infer only indexing metadata such as:

- a short neutral title;
- one primary category;
- `applies_to` categories.

It must not:

- paraphrase the teaching;
- summarize it into different strategic advice;
- correct or soften it;
- add new strategic recommendations;
- remove qualifiers;
- turn conditional guidance into an unconditional rule.

## 5. Authority semantics

Decision authority is conceptually:

```text
1. Legal-action constraints
2. Relevant authoritative human teaching
3. Fixed expert priors
4. Non-authoritative playbook guidance / model judgment
```

Human teaching may guide strategy, but it cannot make an illegal game action executable.

Expert card priors are evidence only and should not overrule relevant human teaching.

## 6. Cross-category teaching

Human feedback often spans multiple decision types. For example, one lesson can discuss both deck construction and combat sequencing.

Therefore every authoritative lesson has:

```text
primary category
applies_to = [one or more retrieval categories]
```

The primary category is an indexing label, not a statement that the teaching is irrelevant elsewhere.

This distinction became important in Run 33: the Run-32 lesson was correctly stored as primary `CARD_REWARD` with `applies_to = [CARD_REWARD, COMBAT]`, but the first focused-memory ranking implementation could still omit it from the bounded combat prompt. The Run-34 v1.2.1 hotfix ranks recent applicable authoritative teaching before primary-category metadata.

## 7. Feedback quality rule

Prefer a small number of **generalizable, evidence-backed lessons** over a long list of run-specific complaints.

Good feedback should answer:

- what pattern was wrong?
- why was it wrong in this trajectory?
- what decision principle should change next time?
- under what conditions should that principle apply?

Avoid teaching one-off actions as universal rules unless they truly are universal.

## 8. Example: Run-32 teaching

Run 32 exposed two recurring issues:

- permanent card choices were justified locally without a coherent long-term build;
- a planned defensive follow-up was abandoned by fresh replanning within the same turn.

The human teaching therefore focused on:

- maintaining an explicit damage/defense/scaling/draw-energy plan;
- adding a card only when it advances a real need or synergy;
- preserving a planned setup→defense sequence unless the state materially changes;
- avoiding preventable HP loss when block is available and extra damage does not meaningfully change the fight.

The lesson was stored as authoritative and applied to both `CARD_REWARD` and `COMBAT`.

## 9. Example: Run-33 teaching

Run 33 showed improved sequencing, so the feedback should not simply repeat the old complaint.

The more useful lesson was:

- if the persistent deck plan identifies a dominant missing role such as long-term scaling, treat that as a real priority;
- do not choose a merely efficient incremental card over a card that directly solves the named bottleneck without a clear reason;
- as the deck matures, raise the threshold for adding another card and prefer Skip when an option does not materially improve the plan;
- preserve the improved sticky sequencing and use the cheapest sufficient defensive resource based on actual mitigation.

This demonstrates the intended feedback style: reinforce what improved, then teach the next unresolved strategic bottleneck.

## 10. Human vs AI-assisted review

If an LLM is used to inspect logs and propose feedback, the safest research description is **AI-assisted human teaching** unless the human independently determines the strategic content.

A defensible workflow is:

```text
trajectory/logs
 -> analysis assistance
 -> human reviews/edits/approves the proposed lesson
 -> only human-approved text becomes authoritative teaching
```

The stored authoritative text should represent what the human actually endorses.

## 11. Audit requirements

For each reviewed run, preserve:

- run number / run ID;
- initial reflection;
- review decision;
- human feedback ID where applicable;
- exact human text;
- final reflection artifact;
- resulting raw-memory ID(s);
- source-memory coverage in the playbook;
- `POST_RUN_REFLECTION_COMPLETE` event.

## 12. Runs 34–36: examples of feedback vs code fixes

- **Run 34:** Correctly ranking newer cross-category teaching was not enough; the remaining top-k cutoff hid older Run-13 combat guidance. **Controller fix (Run 35):** include all applicable cumulative rules, with context pinning. This was not a new human lesson.
- **Run 35:** The agent estimated 49 Block against Collector while active Frail reduced supported cards to 36 effective Block. **Controller fix (Run 36):** expose deterministic static Frail/Dexterity Block arithmetic. **Human teaching:** improve tactical survival, scaling and deck-pick reasoning. Do not claim that playing Impervious earlier would fix the missed Frail arithmetic.
- **Run 36:** A queued `End turn` action crossed combat encounters, despite the next fight offering lethal attacks. **Controller fix (Run 37):** encounter-level plan invalidation and end-turn rechecking. **Human teaching:** timing scaling during long fights, HP-risk-aware shops, routes and combat threat assessment.

**Review quality rule:** do not force human teaching to repair execution or data-integrity bugs. Identify the behavioral evidence, the expected strategy and any meaningful exceptions. Distinguish observed facts from counterfactual predictions; a potion or card might have helped but is not guaranteed to save a run.

## 13. Fixed Run-37+ routine

Continue using the exact same feedback web app and action labels. Once Run 37 ends, inspect its trajectory and initial reflection, choose `HUMAN_TEACHING` or `APPROVE_INITIAL`, finalize, and confirm `POST_RUN_REFLECTION_COMPLETE` and `playbook.updated_through_run` before treating the lesson as incorporated.

The fixed controller automatically carries forward the entire cumulative playbook. **Do not copy or swap code between ordinary reviewed runs.** See [stable workflow](C2_STABLE_FEEDBACK_WORKFLOW.md).

At the Run-36 finalized baseline: 50 raw lessons, 36 playbook rules, 36 feedback records. Human feedback selected for later runs should be approved by the actual human reviewer even when AI assistance helped draft it; describe that as AI-assisted human teaching if applicable.
