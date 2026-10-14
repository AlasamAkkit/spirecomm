# Project Log

This log records the major research, architecture, and integrity milestones of the Slay the Spire LLM FYP. Fine-grained implementation changes are tracked in `CHANGELOG.md` and `CONTINUAL_CHANGELOG.md`; stable behavioral findings are tracked in `OBSERVATIONS.md` and `CONTINUAL_OBSERVATIONS.md`.

## 1. Research objective established

The project studies whether persistent cross-run learning can improve an LLM Slay the Spire agent, with a specific comparison between:

- autonomous self-reflection; and
- iterative human teaching.

Learning is implemented through external memory, not model-weight updates.

Core runtime architecture:

```text
Slay the Spire
 -> CommunicationMod
 -> Python controller
 -> constrained legal-action prompt
 -> GPT-5.6 Luna actor
 -> validated command
 -> game
```

## 2. Baseline controller and instrumentation

The controller was expanded beyond simple combat choices to support the major game surfaces required for full-run experiments:

- Neow;
- map decisions;
- events;
- combat cards and targets;
- potions;
- HAND_SELECT / GRID_SELECT;
- card and combat rewards;
- shops and removal;
- campfires;
- boss relics;
- treasure and keys;
- terminal run states.

Structured runtime logging became the machine-readable source of truth for experiments.

## 3. Condition A — 30-run baseline

A 30-run no-memory Ironclad Ascension-0 baseline established starting capability.

Results:

- wins: 0/30;
- mean floor: 23.37;
- median floor: 24;
- best floor: 50;
- mean score: 200.43;
- Act 2: 20/30;
- Act 3: 1/30.

The main recurring problems were mid-Act-2 attrition, permissive deck growth, and imperfect resource/risk management.

## 4. Reflection-v0.2 and Condition B

A post-run reflection pipeline was validated on completed trajectories and then used online in Condition B.

Condition B:

- 30 valid runs;
- autonomous reflection after each run;
- exact-category newest-first retrieval capped at three lessons;
- 85 stored lessons;
- zero detected future-memory leakage.

Results:

- mean floor: 27.23;
- median floor: 28;
- mean score: 236.63;
- Act 2: 22/30;
- Act 3: 3/30;
- wins: 0.

Behavior became more selective: permanent card Skip increased from 2.8% in A to 14.1% in B.

The phase exposed two structural memory limits:

1. older useful rules can age out of the top-3 window;
2. one primary category can hide advice relevant to another decision type.

## 5. Condition C1 — human-curated reflection

C1 inserted human review before lesson storage while preserving B's retrieval mechanism.

Final retained memory:

- 73 lessons;
- 61 accepted;
- 11 corrected;
- 1 human-added.

Human review corrected wrong-cause attribution, missing context, vague or false strategic conclusions, and long-horizon omissions.

This established that lesson quality can improve through human semantic review, while also showing that a better lesson still cannot help if retrieval does not surface it.

## 6. B2/C2 cumulative-memory redesign

To address B/C1 retrieval limitations, both follow-up conditions adopted `cumulative-playbook-v2`:

- permanent raw memory;
- playbook rules with `source_memory_ids`;
- cross-category `applies_to` scopes;
- complete raw-memory source-coverage validation;
- all applicable rules supplied to the actor during the controlled follow-up.

B2 remained autonomous. C2 added human teaching.

## 7. B2 v1.1.0 invalidated; v1.1.1 finalized

The first B2 official batch was invalidated because skipped permanent card rewards could reopen from the parent reward screen.

Measured impact:

- 92 skip decisions;
- 19 reward instances;
- 9 affected runs;
- worst instance: 29 repeated skips.

A deterministic card-reward skip guard fixed the issue and B2 restarted from empty memory.

Final B2 v1.1.1, 15 matched runs:

- wins: 0;
- mean floor: 18.73;
- median floor: 16;
- best floor: 29;
- mean score: 144.60;
- Act 2+: 6/15;
- Act 3: 0/15;
- raw lessons: 38;
- playbook rules: 14;
- 2,924 retrievals;
- zero detected current/future leakage.

## 8. C2 teaching policy redesigned to preserve human strategy verbatim

An early C2 prototype allowed a second LLM to rewrite human feedback. This was removed because it weakened treatment attribution.

Final policy:

```text
authoritative-human-teaching-v1
```

Two outcomes:

- `APPROVE_INITIAL` — store initial lessons unchanged;
- `HUMAN_TEACHING` — store human strategy verbatim; allow metadata-only indexing.

The strategic human text is not paraphrased or consolidated by an LLM.

## 9. C2 v1.2.0 invalidated; v1.2.1 finalized

The first authoritative-teaching attempt was invalidated after Run-1 Neow teaching was stored correctly but its retrieval metadata omitted `GENERAL`, so Run 2 could not retrieve it at Neow.

v1.2.1 added explicit category mappings and a deterministic Neow/start-relic scope safeguard. A dedicated scope smoke passed.

Final C2 v1.2.1, 15 matched runs:

- wins: 0;
- mean floor: 27.33;
- median floor: 23;
- best floor: 50;
- mean score: 251.47;
- Act 2+: 13/15;
- Act 3: 2/15;
- raw lessons: 25;
- playbook rules: 17;
- `HUMAN_TEACHING`: 10;
- `APPROVE_INITIAL`: 5;
- 3,705 retrievals;
- zero detected current/future leakage.

## 10. Controlled B2/C2 result

Matched comparison:

- C2 higher floor on 11/15 seeds;
- mean paired floor gain: +8.60;
- C2 higher score on 10/15 seeds;
- mean paired score gain: +106.87.

Conclusion:

> Authoritative human teaching substantially improved survival and long-horizon progression relative to autonomous self-reflection under the same cumulative-memory design, although neither condition achieved a win.

The controlled analysis is frozen at this point.

## 11. Research direction changed from fixed held-out Phase III to open-ended continual teaching

The first post-B2/C2 plan proposed a fixed extra C2 training block followed by frozen held-out evaluation.

This was superseded by an open-ended longitudinal design:

- continue one C2 agent indefinitely on fresh random seeds;
- preserve the same human-taught memory across runs;
- remain at Ascension 0 until first win, then increase Ascension;
- treat first clear at each Ascension as a milestone;
- allow explicit architecture interventions when accumulated evidence exposes an execution bottleneck;
- document every intervention boundary.

This separates the project into:

1. a completed matched causal comparison; and
2. an exploratory continual-teaching study.

## 12. Continual Runs 16–28 — original architecture

`test_connection_c2_continual_v1.py` wrapped the frozen final C2 controller and added:

- persistent fresh random seed schedule;
- restart-safe seed reuse;
- Ascension progress state;
- same cross-run C2 memory across future Ascensions.

Checkpoint:

```text
spirecomm/runs/C2_continual_v1_0_through_run28/
```

By Run 28, human teaching repeatedly identified poor card selection, weak deck coherence, and bad combat ordering. The fact that these failures persisted despite increasingly explicit teaching suggested the bottleneck had shifted from missing advice to execution architecture.

## 13. Runs 29–32 — expert card prior + first turn planner

The first intervention added:

- fixed expert Ironclad card priors;
- explicit permanent reward scoring including Skip;
- whole-turn combat reasoning.

A v1.1 activation bug was discovered: the inherited main loop could still instantiate the old class. `test_connection_c2_continual_v1_1_1.py` fixed the construction path.

Runs 29–32 therefore use:

```text
c2-continual-teaching-v1.1.1-card-prior-turn-planner
```

Run 29 verified the architecture was genuinely active.

Run 32 exposed the main weakness: the model could plan a setup→defense sequence, execute the first action, then fresh replanning could abandon the planned defense and take avoidable damage.

Run-32 checkpoint:

```text
spirecomm/runs/C2_continual_through_run32_pre_v1_2/
```

Validated values:

- completed/reflected: 32;
- raw lessons: 46;
- playbook rules: 32;
- feedback rows: 32.

## 14. Run 33 — persistent planning intervention

Run 33 begins:

```text
c2-continual-teaching-v1.2.0-persistent-planning
persistent-deck-plan+sticky-turn-plan+focused-memory-v1
```

Changes:

- persistent deck plan across permanent rewards;
- explicit deck weaknesses/priorities/avoid-list;
- deterministic argmax card selection, Skip wins ties;
- sticky within-turn action sequences;
- focused tactical memory: combat 8 rules, card rewards 10.

Run 33 result:

- LOSS;
- Act 2 Floor 33;
- score 292;
- Collector.

Observed improvements:

- planned action ordering was actually followed;
- draw effects triggered deliberate replanning rather than stale execution;
- card skipping became more selective later in the run;
- tactical prompts became smaller.

Remaining strategic issue:

- the deck plan identified long-term scaling as a dominant weakness but still chose Sword Boomerang over Spot Weakness, showing that representing a plan does not guarantee that the evaluator obeys its own bottleneck.

## 15. Run-33 focused-memory audit and Run-34 hotfix

Run-32 authoritative teaching was correctly stored as:

```text
category = CARD_REWARD
applies_to = [CARD_REWARD, COMBAT]
```

v1.2.0 still omitted it from combat's top-8 focused window because primary-category match ranked ahead of recency.

Prepared for Run 34 onward:

```text
c2-continual-teaching-v1.2.1-applicability-recency-hotfix
```

New focused-memory ordering:

```text
applicability filter
 -> authoritative status
 -> source-run recency
 -> primary-category tie-break
 -> GENERAL tie-break
```

Run 33 was finalized with a capped finalize-only wrapper so Run 34 could not start under the old v1.2.0 controller.

## 16. Current state

Latest finalized run: **33**.  
Current Ascension: **0**.  
Next intended run: **34**.  
Next intended controller: `c2-continual-teaching-v1.2.1-applicability-recency-hotfix`.

Current canonical references:

- `CONTINUAL_C2_STATUS.md`
- `CONTROLLER_HISTORY.md`
- `protocols/C2_CONTINUAL_TEACHING_PROTOCOL.md`
- `CONTINUAL_CHANGELOG.md`
- `CONTINUAL_OBSERVATIONS.md`
