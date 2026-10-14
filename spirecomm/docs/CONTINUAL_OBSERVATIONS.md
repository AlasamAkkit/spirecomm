# Continual C2 Observations

This file continues the stable observation record after `OBSERVATIONS.md` (which is preserved through OBS-088).

## OBS-089 — Repeated human teaching exposed an execution bottleneck

By Run 28, the dominant failure pattern was no longer simply missing strategic feedback. The memory already contained repeated guidance on card quality, deck coherence, combat ordering, vulnerable setup, and avoiding needless damage, yet the agent continued to make locally plausible but globally inconsistent decisions.

**Interpretation:** accumulating more textual teaching alone was unlikely to fix the remaining behavior. The continual phase had exposed a decision-architecture limitation.

## OBS-090 — Expert card priors improve inspectability but do not create a deck plan

The Run-29 intervention added fixed expert Ironclad card priors and an explicit permanent card-reward evaluator.

Benefits:

- every permanent option, including Skip, received a visible score;
- card quality became auditable;
- some weak/redundant rewards were skipped.

Limitation:

- a tier prior remains local evidence;
- the agent can still justify individually reasonable cards without committing to a coherent long-term deck strategy.

## OBS-091 — A proposed whole-turn plan can still be behaviorally one-action

Runs 29–32 generated a full-turn combat plan but executed only the first action before replanning from scratch.

Run 32 showed the failure clearly: the model planned a sequence containing setup followed by defense, executed the setup, then the fresh plan abandoned the defensive follow-up and took avoidable damage.

**Interpretation:** asking the LLM to reason about the full turn is insufficient if the controller discards the plan after one action.

## OBS-092 — Persistent deck planning improves reward coherence but does not guarantee plan obedience

Run 33 introduced a persistent run-level deck plan and deterministic score-based permanent reward selection.

The plan tracked offense, defense, scaling, draw/energy, AoE, weaknesses, priorities, avoid-list, and add policy.

The agent became more selective later in the run and produced more explicit Skip decisions. However, it still identified long-term scaling as the deck's principal weakness while choosing Sword Boomerang over Spot Weakness.

**Interpretation:** representing the plan is useful, but the evaluator still needs to weight the plan's named bottleneck strongly enough to affect selection.

## OBS-093 — Deterministic score selection removes one source of inconsistency

Beginning with Run 33, the permanent card evaluator no longer returns an unconstrained final `choice` independent of its score table.

The controller selects the numerical argmax and gives Skip exact-tie preference.

**Benefit:** model reasoning and controller selection are auditable from the same score representation; a free-form choice cannot silently contradict the scores.

## OBS-094 — Sticky within-turn plans materially improve action ordering

Run 33 showed that committed action sequences were actually followed when the next semantic action remained legal.

Examples included:

- setup before payoff;
- planned defensive cards actually being played after offensive setup;
- avoiding defensive cards when the enemy was not attacking;
- preserving strong exhaust/limited defensive cards when ordinary block was calculated to be sufficient.

Draw-changing actions could intentionally stop the sequence so the controller replanned with the new hand.

**Interpretation:** controller-level commitment closed the specific Run-32 plan-abandonment failure mode.

## OBS-095 — Focused retrieval substantially reduces tactical prompt growth

Before the focused-memory intervention, a combat decision could receive more than twenty applicable playbook rules and produce prompts around ~18k characters.

Run 33 bounded tactical memory to:

```text
COMBAT: 8 rules
CARD_REWARD: 10 rules
```

Observed combat prompts were materially smaller while preserving permanent raw memory for auditability.

**Trade-off:** bounded retrieval introduces a ranking problem that must be correct.

## OBS-096 — `applies_to` eligibility must outrank primary-category metadata

Run-32 authoritative teaching was stored correctly with:

```text
category = CARD_REWARD
applies_to = [CARD_REWARD, COMBAT]
```

During Run 33, v1.2.0 combat retrieval still omitted the lesson because old rules with primary `COMBAT` category ranked ahead of the recent cross-category lesson and filled the top-8 window.

**Interpretation:** once applicability has declared a rule relevant, primary category should not hide a much newer authoritative rule.

Run-34 v1.2.1 fixes ranking to prefer authority and recency before primary-category tie-breaking.

## OBS-097 — Initial autonomous reflection can misdiagnose a tactical decision

The Run-33 initial reflection criticized failing to use Apparition+ during a Collector turn with multiple attackers.

The actual planner trace showed that it intentionally chose Iron Wave plus two Defend+ cards because it calculated that ordinary block would fully cover the Torch Head attacks while preserving Apparition+ and Impervious.

**Interpretation:** post-run reflection should be checked against the model's actual decision rationale and available state before the lesson is accepted. A superficially plausible failure narrative can be wrong.

## OBS-098 — Human feedback should evolve instead of repeating old lessons

Run 33's sticky sequencing was substantially better than Run 32. Repeating “preserve the full-turn plan” as if nothing changed would provide little new information.

The more useful Run-33 teaching targeted the next bottleneck:

- obey the dominant weakness identified by the persistent deck plan;
- raise the threshold for card additions as the deck matures;
- preserve strong limited defensive resources only when ordinary mitigation is actually sufficient.

**Interpretation:** continual teaching should reinforce improvements but spend memory budget on unresolved generalizable failures.

## OBS-099 — Continual controller changes require explicit experimental boundaries

Runs 16–28, 29–32, Run 33, and Run 34+ use materially different decision architectures.

Therefore continual results should be analyzed by controller era rather than pooled as though one frozen policy produced every run.

This does not affect the completed B2/C2 causal comparison, which remains frozen and separate.

## OBS-100 — Post-run finalization and next-run startup are separate safety concerns

A gameplay `RUN_END` can exist before human review and `POST_RUN_REFLECTION_COMPLETE`.

Relaunching a normal controller in this state may finish the old reflection and immediately start the next run under the same controller. This is unsafe at an intervention boundary.

Finalize-only wrappers for Runs 32 and 33 demonstrated the safer pattern:

```text
finish pending reflection
cap completed runs at boundary
verify playbook updated_through_run
close controller
switch version
preflight
start next gameplay run
```

This is now the preferred procedure for future controller transitions.
