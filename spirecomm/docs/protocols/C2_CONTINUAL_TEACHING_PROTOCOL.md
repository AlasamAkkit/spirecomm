# C2 Continual Human-Teaching Protocol

> **Status:** ACTIVE / LONGITUDINAL  
> **Current finalized checkpoint:** Run 33  
> **Next gameplay controller:** `c2-continual-teaching-v1.2.1-applicability-recency-hotfix` from Run 34 onward

## 1. Purpose

After the matched B2/C2 experiment showed better progression under authoritative human teaching, C2 became the architecture selected for continued study.

This phase asks a different question from the controlled B2/C2 comparison:

> How far can continued authoritative human teaching push the same Slay the Spire agent over repeated runs, and what execution or planning limits emerge as the teaching accumulates?

This is an **exploratory longitudinal phase**, not a matched causal benchmark. Controller changes are therefore permitted when accumulated evidence exposes a clear architectural bottleneck, but every change must create an explicit version boundary.

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

### Run 34 onward — v1.2.1 focused-memory ranking hotfix

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

## 5. Developed but unused controller

`test_connection_c2_continual_v1_1_2.py` implemented a narrow deterministic human-authority/hard-card-prohibition layer. It was developed after an observed card-prior conflict, but its planned run boundary became stale and it was **not used as an experimental run phase**.

Do not attribute any completed continual run to v1.1.2.

## 6. Reflection/finalization safety

A completed gameplay run may have `RUN_END` before its human review and `POST_RUN_REFLECTION_COMPLETE` have been written. Relaunching the normal controller in that state can finalize the previous run and then immediately start the next run under the same controller.

For version-boundary transitions, use finalize-only wrappers capped at the completed run count. Existing examples:

```text
spirecomm/test_connection_c2_finalize_run32.py
spirecomm/test_connection_c2_finalize_run33.py
```

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

## 9. Current next step

Run 33 is finalized. Before Run 34, activate and preflight:

```text
spirecomm/test_connection_c2_continual_v1_2_1.py
```

Run 34 is the first run intended to use the applicability/recency focused-memory hotfix.
