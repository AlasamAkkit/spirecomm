# Continual C2 run ledger: 33–37

> Finalized through **Run 36**. **Run 37 was reported running; outcome and reflection not yet verified.** Each completed run is attributed to the version recorded at `RUN_START`, not the mutable `test_connection.py` entry point.

| Run | Controller | Result | Floor | Score | Raw lessons after reflection | Playbook rules after reflection | Intervention/evidence |
|---:|---|---|---:|---:|---:|---:|---|
| 32 | v1.1.1 card-prior turn planner | LOSS | 16 | 106 | 46 | 32 | Pre-v1.2 checkpoint, 32 feedback rows |
| 33 | v1.2.0 persistent-planning | LOSS | 33 | 292 | Not repeated here | Not repeated here | Sticky action sequences and deck plan active; focused-memory rank bug discovered |
| 34 | v1.2.1 applicability/recency | LOSS | 22 | 194 | **48** | **34** | Pre-v1.3 checkpoint; older Run-13 encounter teaching could fall below top-k |
| 35 | v1.3.0 cumulative-policy verified | LOSS | 33 | 273 | **49** | **35** | No top-k; 146 combat verifications with 55 plan replacements observed; Frail block-overestimate identified |
| 36 | v1.3.1 block-aware verifier | LOSS | 23 | 193 | **50** | **36** | 108 `BLOCK_PROJECTION_V131` events, 10-regression-test baseline prepared; stale sticky End turn from another fight found |
| 37 | v1.4.0 stable feedback loop | **In progress / not confirmed complete** | — | — | — | — | First fixed-controller evaluation run |

## Validated checkpoints

- `spirecomm/runs/C2_continual_through_run32_pre_v1_2/`
- `spirecomm/runs/C2_continual_through_run33_pre_v1_2_1/`
- `spirecomm/runs/C2_continual_through_run34_pre_v1_3/` — Run 34, 48 lessons, 34 rules
- `spirecomm/runs/C2_continual_through_run35_pre_v1_3_1/` — Run 35, 49 lessons, 35 rules
- `spirecomm/runs/C2_continual_through_run36_pre_stable/` — created **locally** by `activate_c2_stable.py`; not assumed present in GitHub unless subsequently committed/pushed

## Run 34: more than a ranking bug

Run-33 audit found `applies_to`-eligible newer teaching misranked; v1.2.1 corrected priority. However the Run-34 review showed the **top-k cutoff itself** could exclude older authoritative encounter-specific teaching. Storing a lesson in raw memory/playbook did not mean the actor saw it. This motivated the all-applicable retrieval policy from Run 35.

## Run 35: cumulative retrieval and mathematical verification

Cumulative raw lesson coverage was 48/48 before starting. The Run-13 Centurion/Mystic preference appeared again in retrieved policy and was followed in a relevant encounter. The independent combat verifier operated and changed plans, but in the Collector fight printed block values were mistaken for effective values. Under Frail, 11 + 30 + 8 printed Block becomes 8 + 22 + 6 = **36**, not 49. The agent died with 5 HP against 46 incoming damage after generating 36 Block. Run-35 human review added explicit teaching on precise defense, survival, scaling and deck selection.

## Run 36: Block fix works, but executor boundary fails

The new projection acknowledged Frail/Dexterity and produced 108 audit events during gameplay. The agent still lost at Act 2 Floor 23 (Gremlin Leader encounter). Spheric Guardian consumed substantial HP and the final low-HP path was fragile. A stale queued `End turn` was also found crossing from an earlier combat to a later fight whose first turn had the same run/turn identifiers. This is **controller code**, not a lesson the human should need to teach.

The v1.4.0 boundary therefore fixes encounter identity, invalidates old queued actions across room changes, drops queued end turns for live re-verification, and checks known avoidable damage before ending turns. Its 10 deterministic regression tests passed locally at stable activation.

## Interpreting the ledger

- **Avoid false causality:** Run 35 performing better than 36 by floor/score does not mean v1.3.1 hurt the agent; both seed and controller changed.
- **Memory inclusion != successful learning:** `memory_top_k = null` and `omitted_memory_count = 0` establish retrieval availability; action logs are needed to establish correct application.
- **Static Block projection != full simulator:** unknown effects, uncertain intents, relic interactions and future drawn cards remain unmodeled.
- **Stable evaluation:** Runs 37 onward should share one fixed version; attribute later changes primarily to growing memory, feedback and different seeds, with the usual observational caveats.

Related: [SYSTEM_ARCHITECTURE_AND_RETROSPECTIVE.md](SYSTEM_ARCHITECTURE_AND_RETROSPECTIVE.md), [CONTROLLER_HISTORY.md](CONTROLLER_HISTORY.md), [C2_STABLE_FEEDBACK_WORKFLOW.md](C2_STABLE_FEEDBACK_WORKFLOW.md).
