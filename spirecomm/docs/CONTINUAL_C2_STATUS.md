# Continual C2 Status

> **Updated 2026-11-11.** Run 48 completed A10 LOSS at Floor 13, score 134 using v1.6.0; user reports Run-48 human feedback finalized. Run-49 v1.6.1 source and offline checks are prepared. **Local finalization evidence/checkpoint and live Run 49 are not verified by GitHub.**

## Current operational state

| Item | State |
|---|---|
| Active launcher | spirecomm/test_connection.py → test_connection_c2_run49.py |
| Controller variant | c2-v1.6.1-run49-equivalent-card-xcost-guard+a10 |
| Difficulty | A10, fixed since Run 39 |
| Latest completed gameplay | Run 48, LOSS Floor 13, score 134, three Sentries |
| Human review | Run 48 feedback reported finalized; confirm local FINALIZED, POST_RUN_REFLECTION_COMPLETE and playbook >= 48 |
| Before Run 49 | Create write-once C2_through_run48_pre_v1_6_1.zip locally, then pass offline checks |
| Verification | v1.6.1 offline tests; **live Run 49 not yet verified** |

## Fixed matched B2/C2 study (unchanged)

15 matched seeds each, Ascension 0. B2 autonomous: mean floor 18.73, mean score 144.60, 0/15 wins. C2 human-taught: mean floor 27.33, mean score 251.47, 0/15 wins. C2 was higher on 11/15 seeds by floor. Later continual A10 runs are not part of this controlled comparison.

## Longitudinal controller boundaries

| Runs | Version | Evidence |
|---|---|---|
| 16–36 | v1.0–v1.3.1 | Exploratory controller/memory interventions |
| 37–38 | v1.4 | A0 win then A1 loss |
| 39–42 | v1.4 + A10 | Four A10 loss trajectories |
| 43–47 | v1.5 + A10 | Neow human supersession + conservative verifier; Run 45 reached Floor 37 |
| 48 | v1.6.0 + A10 | First live run; 12 false duplicate-card invalidations; zero-energy Whirlwind verifier error |
| 49+ | v1.6.1 + A10 | Equivalent copies, exact target preservation, and X-cost verification; live outcome pending |

## Run-49 startup repair

The original Run-48 freezer script incorrectly expected playbook through Run 47 while requesting a Run-48 archive. A tested fix now requires Run 48. **If the agent refuses to start, run `python .\spirecomm\diagnose_run49_startup.py` after pulling master; do not cycle the game repeatedly.** The read-only script reveals missing checkpoints, unfinalized reviews and playbook/event gaps.

## Run 49 safe cutover

Stop game/controller, preserve local changes and pull updated master only after protecting uncommitted work. Verify Run 48 FINALIZED, playbook updated_through_run >= 48 and POST_RUN_REFLECTION_COMPLETE. Run python .\spirecomm\freeze_c2_run48_checkpoint.py once, then stable/A10/Run43/Run48/Run49/reflection preflights. Start Run 49 and check RUN_START controller_variant, active_ascension: 10 and new RUN49 audit events.

Human review still controls authoritative teaching. Do not blame the acting agent for verifier replacements or target-match invalidation. Neither an offline test pass nor isolated seed-to-seed floor difference proves improved win rate.

See [Run-49 guide](RUN49_CONTROLLER_V161.md), [historical Run-48 guide](RUN48_CONTROLLER_V16.md), [A10 ledger](RUNS_39_48_A10_EVALUATION.md), [controller history](CONTROLLER_HISTORY.md), and [logging schema](LOGGING_SCHEMA.md).
