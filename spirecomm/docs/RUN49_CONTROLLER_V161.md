# Run 49: v1.6.1 equivalent-card and X-cost guard

> **Current operating guide (2026-11-11).** Run 48 on v1.6.0 ended LOSS at Act 1 Floor 13, score 134. The reviewer reports Run 48 feedback finalized. This GitHub branch contains versioned v1.6.1 source and offline tests; there is **no verified live Run 49 result** and GitHub does not contain the local finalized checkpoint.

## What Run 48 exposed

- **12 false sticky-plan invalidations:** Two playable Strikes on the same Lagavulin, duplicated Defends and duplicated Pommel Strikes had the same description and same intended enemy. The v1.6 matcher required exactly one match, so it discarded valid remaining plans and requested a fresh LLM decision. This is not the original Run-46 wrong-Sentry-target failure.
- **X-cost arithmetic:** At zero energy on Floor 8, the acting LLM proposed End turn. The verifier claimed playing Whirlwind would deal five damage to every Slime, selected Whirlwind instead, and no such damage was observed. Whirlwind spends current energy and hits once per energy spent. Chemical X changes X-cost behavior; card-play relics such as Kunai can occasionally reward an otherwise zero-damage attack.
- **Positive evidence:** Neow relic-swap human supersession remained active, three infeasible first-pass plans were rejected and the controller used the correct v1.6.0 marker. The run outcome alone does not prove the controller change harmed performance.

## v1.6.1 fix (Run 49 onward)

1. Keep the **original monster slot, name, max HP and available identity field**. Resolve repeated PLAY actions by checking currently exposed card-effect fields: name, upgrade level, cost, per-turn cost, base damage/block/magic values, misc, and modifiers. If copies are equivalent, prefer an exact surviving card UUID, otherwise select the lowest current hand slot. If card effects differ or the enemy identity changed, invalidate and replan. No automatic same-name enemy retargeting.
2. When a verifier tries to replace the original End-turn plan with a zero-energy Whirlwind, reject unsupported positive-damage reasoning unless Chemical X is present or the verifier identifies an explicit non-damage attack-play trigger and acknowledges zero damage. Add the X-cost rule to verifier prompts; do not ban all zero-energy X cards or proven legitimate Kunai synergies.
3. New audit events: RUN49_EQUIVALENT_CARD_MATCH, RUN49_STICKY_TARGET_REPLAN, RUN49_X_COST_REPLACEMENT_REJECTED, RUN49_VERIFIER_CARD_BINDING. Inherited RUN48 feasibility events remain. C2 reflection provenance includes both v1.6.0 and v1.6.1 intervention events.
4. **New controller marker:** c2-v1.6.1-run49-equivalent-card-xcost-guard+a10. Previous Run-48 controller and raw data remain unchanged.

## Limitations and experimental integrity

The guard detects the reported failure modes and a bounded set of card-effect fields. It is not a full combat/card/relic simulator, does not predict dynamic future draws or all attack-play synergies, and cannot prove all same-name enemy instances remain unchanged without game-provided identity. Ambiguous different-effect copies trigger conservative replanning. Run 49 is a separate intervention, not a continuation of an unchanged fixed-controller cohort. Independent seeds and accumulated human memory confound simple floor comparisons.

## Startup-repair note (2026-11-11)

The initial v1.6.1 release contained an error in `freeze_c2_run48_checkpoint.py`: it checked `updated_through_run != 47` while reporting that the required Run-48 value was 48. This blocked creation of the mandatory Run-48 archive when the playbook was correctly finalized through Run 48, preventing `ContinualC2Run49Agent` from starting. The comparison is now correctly `!= 48`, with tests that actually create a synthetic archive and reject an incorrect playbook.

**Do not repeatedly restart STS to debug this gate.** After pulling the fix, close the game/controller, run the corrected freezer, then run the read-only diagnostic:

```powershell
python .\spirecomm\freeze_c2_run48_checkpoint.py
python .\spirecomm\diagnose_run49_startup.py
```

The diagnostic verifies the historical Run-42/47 checkpoint prerequisites, Run-48 checkpoint ZIP, finalized review, and playbook/ledger flags without changing data or starting the game. If it returns `RUN-49 STARTUP GATES PASS` but gameplay still does not start, inspect the actual controller terminal traceback and CommunicationMod connection logs. Do not delete or overwrite local checkpoints.

## Required local cutover before Run 49

1. Stop STS and the controller. Verify that run_48_feedback_review.json has status FINALIZED, the local playbook has updated_through_run >= 48, and run_events_c2.jsonl contains POST_RUN_REFLECTION_COMPLETE with completed_run_number 48.
2. Preserve uncommitted logs and raw teaching. Run git status --short; then safely run git pull --ff-only origin master. Do **not** use destructive git reset/clean.
3. Run python .\spirecomm\freeze_c2_run48_checkpoint.py while STS is stopped. It creates the write-once, gitignored spirecomm/runs/_local_checkpoints/C2_through_run48_pre_v1_6_1.zip. GitHub contains the freezer script, not the local ZIP.
4. Run offline checks:

   python .\spirecomm\test_c2_stable_preflight.py
   python .\spirecomm\test_c2_a10_policy.py
   python .\spirecomm\test_c2_run43_preflight.py
   python .\spirecomm\test_c2_run48_preflight.py
   python .\spirecomm\test_c2_run49_preflight.py
   python -m unittest discover -s .\reflection\tests -p test_*.py -v

5. Start the game with CommunicationMod using spirecomm/test_connection.py. Confirm RUN_START for **Run 49, Ascension 10** and the v1.6.1 controller marker. Monitor the new RUN49 events during duplicate-card and X-cost encounters. This is a **live validation** run; offline CI alone cannot guarantee gameplay correctness.

## Phase boundaries

v1.4 Runs 37–42 (A10 from Run 39); v1.5 Runs 43–47; v1.6.0 Run 48; v1.6.1 Run 49 onward. Preserve frozen matched B2/C2 datasets and earlier run results verbatim. See [controller history](CONTROLLER_HISTORY.md), [current status](CONTINUAL_C2_STATUS.md) and [Run-48 historical guide](RUN48_CONTROLLER_V16.md).
