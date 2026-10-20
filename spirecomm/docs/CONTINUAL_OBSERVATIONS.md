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

Runs 16–28, 29–32, 33, 34, 35, 36 and the fixed Run-37+ phase use explicitly distinguished decision architectures.

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

## OBS-101 — Correct memory ranking does not imply cumulative recall

Run 34 corrected the precedence of applicable recent authoritative teaching, but fixed top-k limits still removed **older** human encounter advice from actor prompts. `source_memory_ids` being present in the playbook was not enough. Run-35 all-applicable retrieval removed the cutoff and allowed old Centurion/Mystic advice to be retrieved again.

**Interpretation:** study memory *coverage at retrieval time*, not only storage count. The prompt must contain applicable guidance before compliance can even be tested.

## OBS-102 — Retrieval presence and behavioral compliance are distinct

Run 35's `memory_top_k=null` and zero omission demonstrate retrieval, while the combat action/verification trace demonstrates the specific encounter teaching was applied. Neither metric alone is a general proof of self-improvement.

## OBS-103 — Second-pass verification can reproduce first-pass numerical errors

Run 35 used 146 plan verifications and replaced 55 plans, yet the Collector turn still showed an overestimate from printed rather than Frail-adjusted Block. The verifier is a fallible reasoning model; approval is not equivalent to deterministic legal or numerical validation.

## OBS-104 — Effective Block must reflect status effects per card

The Run-35 example: Shrug It Off+ (11 printed), Impervious (30), Defend+ (8) sum to 49. Under Frail they provided **8+22+6=36**. v1.3.1 added a bounded static projection with Frail and Dexterity, explicitly not a full game simulator.

## OBS-105 — Sticky combat identity must include encounter context

Run 36 showed an old queued End-turn crossing from one combat to another because the run ID and turn number were equal and End-turn remained legal. The v1.4 controller clears the sticky plan on room/encounter changes and re-verifies queued End-turn rather than trusting old approval.

## OBS-106 — End-turn overrides can themselves be harmful without relic awareness

A naive "always play Defend before taking damage" guard can disable Orichalcum's free end-turn Block and worsen the outcome. The fixed guard compares the supported defensive candidate against the known passive baseline, with regression tests for better/worse cases.

## OBS-107 — Strategic failures must be separated from code defects

Prolonged Spheric Guardian combat, skipped damage rewards and low-HP shops in Run 36 require contextual strategic teaching; cross-encounter action leakage requires a code fix. Treating both as "give the model more advice" would misdiagnose the cause.

## OBS-108 — Changing controller every run confounds feedback evaluation

Runs 16–36 combined architectural changes with accumulating memory. The stable v1.4.0 intervention establishes a fixed Run-37+ period, with 10 passing preflight tests and a Run-36 baseline checkpoint, so future analysis can focus on learned guidance and actual decision behavior rather than constant engineering adjustments.

**Evaluation caveat:** Runs 37+ use independent seeds. Even with fixed code, isolated score differences are not causal evidence. Evaluate across a window and audit specific old/new teaching applications.
