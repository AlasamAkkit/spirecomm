# C2 Continual Human-Teaching Protocol

> **Status:** ACTIVE / LONGITUDINAL  
> **Most recent finalized/reflected run:** 36 (50 raw lessons, 36 rules, 36 feedback records)  
> **Current controller:** `c2-continual-teaching-v1.4.0-stable-feedback-loop`, starting Run 37  
> **Run 37:** in progress at last report; outcome not verified

## 1. Purpose

After the matched B2/C2 experiment showed better progression under authoritative human teaching, C2 became the architecture selected for continued study.

This phase asks a different question from the controlled B2/C2 comparison:

> How far can continued authoritative human teaching push the same Slay the Spire agent over repeated runs, and what execution or planning limits emerge as the teaching accumulates?

This is an **exploratory longitudinal phase**, not a matched causal benchmark. Controller changes were permitted during the exploratory engineering interval (Runs 16–36) when evidence exposed a bottleneck; every change created an explicit run/version boundary. From Run 37 onward, the controller is intentionally fixed for evaluating iterative human teaching.

## 2. Continual-learning rules

- character: Ironclad;
- begin at Ascension 0;
- use a fresh unique random seed for each new run;
- persist the same C2 raw memory and playbook across runs;
- human review remains enabled after every completed run;
- advance Ascension after the first win at the current Ascension;
- continue until project/time/API limits or another explicit stop criterion;
- never silently relabel an earlier run with a later controller version.

The first 15 C2 runs are the completed matched experiment. Continual teaching begins at Run 16 while preserving the learned C2 memory accumulated during Runs 1–15.

## 3. Human-teaching policy

The policy remains `authoritative-human-teaching-v1`.

After each completed run:

1. generate the initial autonomous reflection;
2. review the trajectory and reflection;
3. choose one of:
   - `APPROVE_INITIAL`; or
   - `HUMAN_TEACHING`;
4. if human teaching is supplied, store the strategic text verbatim;
5. allow an LLM to infer only retrieval metadata such as title, primary category, and `applies_to`;
6. preserve full raw-memory provenance and update the cumulative playbook before the next run.

Human teaching is the highest strategic authority below legal-action constraints.

## 4. Run/controller intervention history

### Runs 16–28 — continual teaching v1.0

Controller family:

```text
c2-continual-teaching-v1.0
```

Key properties:

- wrapper over the frozen C2 v1.2.1 controlled controller;
- persistent C2 memory;
- fresh unique 9-digit seed schedule;
- Ascension progression state persisted across restarts;
- one-action tactical architecture inherited from the controlled phase.

Checkpoint:

```text
spirecomm/runs/C2_continual_v1_0_through_run28/
```

By Run 28, repeated human teaching had exposed persistent problems in card selection, deck coherence, and combat action ordering. Run-28 human feedback explicitly criticized playing defense when enemies were not attacking, attacking before applying Vulnerable, taking cards without a coherent build, and poor ordering.

### Runs 29–32 — card priors + replan-every-action turn planner

Active controller:

```text
c2-continual-teaching-v1.1.1-card-prior-turn-planner
```

Changes:

- fixed expert Ironclad card priors from `reflection/ironclad_card_priors.json`;
- explicit permanent-card-reward scoring including Skip/Singing Bowl;
- whole-turn combat plan generated before the first action;
- only the first action executed;
- fresh planning call after each action.

Run 29 confirmed the card evaluator and turn-planner calls were actually active after a v1.1 activation bug had been discovered and fixed by the v1.1.1 wrapper.

The phase exposed a deeper problem: because the plan was discarded after its first action, the next fresh plan could contradict the original sequence. In Run 32, the agent first planned `Bash+ -> Shrug It Off -> End`, then after Bash+ replanned and chose Pommel Strike instead, taking avoidable damage. This showed that nominal whole-turn reasoning did not guarantee behavioral commitment to the planned sequence.

Checkpoint immediately before the next architecture intervention:

```text
spirecomm/runs/C2_continual_through_run32_pre_v1_2/
```

At that checkpoint:

- completed/reflected runs: 32;
- raw lessons: 46;
- playbook rules: 32;
- feedback rows: 32.

### Run 33 — persistent planning v1.2.0

Controller:

```text
c2-continual-teaching-v1.2.0-persistent-planning
```

Decision architecture:

```text
persistent-deck-plan+sticky-turn-plan+focused-memory-v1
```

Intervention components:

#### Persistent deck plan

Permanent card rewards maintain a run-level strategy representation containing:

- offense plan;
- defense plan;
- scaling plan;
- draw/energy status;
- AoE status;
- named weaknesses;
- acquisition priorities;
- cards/effects to avoid;
- add policy.

Each permanent card reward is evaluated against that plan rather than only against local card quality.

#### Deterministic reward selection

The model scores all remaining permanent reward options, including Skip. The controller chooses the numerical argmax; Skip wins exact ties. This removes disagreement between a free-form model `choice` field and its own scores.

#### Sticky within-turn combat plans

The model returns an ordered action sequence. The first action is executed, and subsequent planned semantic actions are followed while they remain legal. Plans are invalidated/recomputed when the turn/run changes or when a planned continuation is no longer valid. Draw-changing decisions can intentionally stop the sequence and trigger replanning.

#### Focused memory

Instead of injecting every applicable rule into high-frequency tactical prompts:

- combat limit: 8 rules;
- permanent card-reward limit: 10 rules.

Complete raw memory remains stored for auditability.

#### Run 33 outcome

- result: LOSS;
- Act reached: 2;
- floor: 33;
- score: 292;
- death: Collector;
- final keys: none.

Run 33 showed substantially more coherent action ordering and meaningful card skipping, but the persistent deck plan still sometimes preferred an incremental local upgrade over the strategic weakness it had itself identified. In particular, the plan identified long-term scaling as weak yet selected Sword Boomerang over Spot Weakness.

### Run 34 only — v1.2.1 focused-memory ranking hotfix

Controller:

```text
c2-continual-teaching-v1.2.1-applicability-recency-hotfix
```

Decision architecture:

```text
persistent-deck-plan+sticky-turn-plan+focused-memory-v1.1
```

The Run-33 audit exposed a focused-retrieval ranking bug. Run-32 authoritative teaching had:

```text
primary category = CARD_REWARD
applies_to = [CARD_REWARD, COMBAT]
```

It was therefore valid for COMBAT, but v1.2.0 ranked a rule's primary category ahead of recency. Older `COMBAT`-primary rules filled the top-8 combat window before the newer Run-32 cross-category rule.

v1.2.1 changes only focused-memory ranking/logging:

1. `retrieve_memories(category)` remains the applicability filter;
2. authoritative teaching outranks non-authoritative rules;
3. among applicable authoritative rules, newer source runs rank ahead of primary-category metadata;
4. primary category is only a tie-breaker after authority and recency.

Memory policy identifier:

```text
focused_authority_applicability_recent_v1
```

### Run 35 — v1.3.0 cumulative retrieval and independent verification

Run 34 showed that improving the focused-memory ranking still left older authoritative advice outside the top-k cutoff. Run 35 therefore used:

```text
c2-continual-teaching-v1.3.0-cumulative-policy-verified-planning
all_applicable_rules_no_topk_with_context_pinning_v1
```

Every applicable playbook rule is included regardless of recency. The Run-13 Centurion/Mystic lesson is a documented retrieval/behavior example. A second model pass verifies newly-created combat turn plans and can replace them. This improves inspectability but does **not** guarantee perfect calculations; Run 35's Collector fight revealed printed Block being confused with Frail-adjusted Block.

### Run 36 — v1.3.1 Block projection

```text
c2-continual-teaching-v1.3.1-block-aware-verifier
```

The controller supplies deterministic effective Block estimates for a supported subset of Ironclad cards (Frail and Dexterity accounted for separately per card), alongside explicit uncertainty for unmodeled effects. The run reported 108 block-projection events. The agent lost on Act 2 Floor 23 after a costly Spheric Guardian encounter. A separate **execution defect** was also discovered: a queued End-turn action could cross into a new encounter that reused the same turn number.

### Run 37 onward — fixed v1.4.0 evaluation

```text
c2-continual-teaching-v1.4.0-stable-feedback-loop
```

This controller is the fixed intervention boundary for a proposed evaluation window, initially Runs 37–50. It preserves cumulative memory, deck planning and verified combat while invalidating stale queued plans at encounter transitions, rechecking queued End-turn actions, and overriding an unsafe End-turn with a legal effective Block card in supported cases.

A one-time local activation validated the Run-36 finalized checkpoint (**36 runs, 50 raw lessons, 36 playbook rules**) and passed **10/10 regression tests**. The user subsequently reported Run 37 actively playing. **Do not claim a Run-37 result until the log confirms it.**

### Stable-phase rule (methodological amendment)

For fixed-controller Runs 37+, **do not rewrite gameplay/learning code after every poor run**. Continue the same `RUN_END -> initial reflection -> human review -> final memory/playbook -> next run` cycle. Fix code only for demonstrable software or data-integrity defects; when unavoidable, freeze a checkpoint and record a new intervention boundary.

This creates a clearer research comparison: Runs 16–36 explore teaching plus architecture changes, whereas the fixed phase observes accumulating teaching with the implementation held constant (still on independent seeds, not a matched causal trial).

See [stable workflow](../C2_STABLE_FEEDBACK_WORKFLOW.md), [system retrospective](../SYSTEM_ARCHITECTURE_AND_RETROSPECTIVE.md), and [run ledger](../CONTINUAL_RUN_LEDGER_33_37.md).

## 5. Developed but unused controller

`test_connection_c2_continual_v1_1_2.py` implemented a narrow deterministic human-authority/hard-card-prohibition layer. It was developed after an observed card-prior conflict, but its planned run boundary became stale and it was **not used as an experimental run phase**.

Do not attribute any completed continual run to v1.1.2.

## 6. Reflection/finalization safety

A completed gameplay run may have `RUN_END` before its human review and `POST_RUN_REFLECTION_COMPLETE` have been written. Relaunching the normal controller in that state can finalize the previous run and then immediately start the next run under the same controller.

For version-boundary transitions, use finalize-only wrappers capped at the completed run count. Historical examples:

```text
spirecomm/test_connection_c2_finalize_run32.py
spirecomm/test_connection_c2_finalize_run33.py
spirecomm/test_connection_c2_finalize_run34.py
spirecomm/test_connection_c2_finalize_run35.py
spirecomm/test_connection_c2_finalize_run36.py
```

Run 37+ normally continues with one fixed controller; use the prior-version wrappers only for past intervention-boundary recovery.

Only switch to the next gameplay controller after the previous run has:

- `POST_RUN_REFLECTION_COMPLETE`;
- final reflection artifact;
- finalized review artifact;
- playbook `updated_through_run` equal to the completed run number.

## 7. Source-of-truth and provenance

For each run, the structured event log is authoritative for runtime decisions and controller metadata.

Important event types now include:

- `RUN_START` / `RUN_END`;
- `MEMORY_RETRIEVAL`;
- `LLM_CALL`;
- `ACTION`;
- `POST_RUN_REFLECTION_COMPLETE`;
- `STICKY_COMBAT_PLAN_CREATED`;
- `STICKY_COMBAT_PLAN_FOLLOWED`;
- `STICKY_COMBAT_PLAN_INVALIDATED`;
- card-reward evaluation events;
- deterministic safety/hard-constraint events where applicable.

Every architecture change must be identifiable from run metadata such as:

```text
continual_controller_version
decision_architecture
intervention_start_run
research_phase
```

## 8. Interpretation rule

The controlled B2/C2 experiment answers whether authoritative human teaching improved outcomes under a matched cumulative-memory design.

The continual phase answers a different question: how learning and architecture co-evolve when persistent human teaching exposes new execution bottlenecks.

Therefore:

- do not pool continual runs into the controlled B2/C2 causal comparison;
- compare continual behavior descriptively across explicit controller eras;
- treat architecture interventions as exploratory changes, not as additional randomized treatments;
- preserve failed/invalidated implementations because they explain why later changes were necessary.

## 9. Stable feedback evaluation: active operation

**Latest finalized:** Run 36, 50 raw lessons, 36 playbook rules.  
**Run 37:** reported in progress, stable v1.4.0; final outcome not yet known.

The one-time stable activation completed locally with **10/10 regression tests passed**. **Do not rerun setup or copy another controller while Run 37 is active.** The fixed controller should remain unchanged across subsequent teaching runs.

At the end of each run:

1. Generate trajectory and initial reflection.
2. Human reviews and selects `APPROVE_INITIAL` or `HUMAN_TEACHING` in the feedback app.
3. Confirm `POST_RUN_REFLECTION_COMPLETE` and `playbook.updated_through_run` for that run.
4. Continue the next run under the **same** `c2-continual-teaching-v1.4.0-stable-feedback-loop` version.

See [stable workflow](../C2_STABLE_FEEDBACK_WORKFLOW.md). Future code changes should be reserved for verified infrastructure/data-integrity defects, each with a new documented boundary.
