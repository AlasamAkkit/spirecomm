# Continual C2 A10 ledger: Runs 37–48

> **Updated 2026-11-11.** Run 48 completed at A10 (LOSS, Floor 13, score 134). The reviewer reports Run 48 feedback finalized; local event/playbook finalization and the pre-v1.6.1 checkpoint remain private and must be checked on the playing machine. v1.6.1 is prepared for Run 49, with **no live Run-49 result**.

## Run-phase separation

| Run(s) | Ascension | Controller | Known state |
|---|---:|---|---|
| 37 | A0 | v1.4 stable | First win, Act 3 Floor 51, score 707 |
| 38 | A1 | v1.4 stable | Loss, Act 2 Floor 21, score 184 |
| 39–42 | A10 | v1.4 stable with fixed A10 wrapper | Four completed loss trajectories; Run 42 reported finalized |
| 43–47 | A10 | v1.5 Run-43 intervention | Five completed loss trajectories, human review through Run 47 reported finalized |
| 48 | A10 | v1.6.0 Run-48 intervention | LOSS, Floor 13, score 134; human feedback reportedly finalized |
| 49 onward | A10 | v1.6.1 Run-49 intervention | Source and offline tests ready; live result unverified |

All results after Run 38 belong to a distinct **A10 stress-test** setting. Do not add them to the frozen matched-seed B2/C2 treatment or control.

## A10 outcomes (reported run reviews)

| Run | Floor reached | Outcome | Notable observation |
|---|---:|---|---|
| 39 | 23 | Loss | First A10 stress phase; v1.4 control |
| 40 | 13 | Loss | Verifier reasoning / damage-estimate concerns |
| 41 | 8 | Loss | Further verifier and energy concerns |
| 42 | 16 | Loss | Conflicting Neow human teaching exposed deterministic supersession gap |
| 43 | 16 | Loss | v1.5 suppressed the Run-1 relic swap in favor of Run-23 correction; verifier numerical errors still observed |
| 44 | 16 | Loss | Continued correct Neow decision; elite attrition / Hexaghost |
| 45 | 37 | Loss | Defeated Act 1 and 2 bosses; reached Transient; deepest reported A10 run through 47 |
| 46 | 8 | Loss | Sentry target-switching and impossible three-Strike verifier plan |
| 47 | 29 | Loss | Defeated Hexaghost; died at Gremlin Leader; unknown-intent policy too blunt |
| 48 | 13 | Loss | Sentries; 12 false duplicate-card sticky invalidations and zero-energy Whirlwind verifier damage error |
| 49 | — | Not yet verified | Versioned v1.6.1 code and offline tests; no live run |

Floor numbers are descriptive, not a paired-seed performance claim. Because independent seeds, changes in controller versions and cumulative feedback all vary, any apparent phase-to-phase improvement is **not causal evidence of the controller change**.

## Interventions and evidence boundaries

**v1.4 (Runs 37–42).** Frozen stable gameplay controller, with fixed A10 difficulty from Run 39. Kept a persistent deck plan, cumulative memory, combat verifier and end-turn safety checks.

**v1.5 (Runs 43–47).** Versioned Neow-specific Run-23-over-Run-1 human instruction supersession, candidate restriction against swapping Burning Blood when alternatives exist, and conservative verifier guards. Raw teaching and playbook history were not rewritten. The memory-supersession behavior was directly observed in these runs. Remaining errors included wrong target continuation, impossible card counts, and blanket unknown-intent rejection.

**v1.6.0 (Run 48).** Queued combat actions are bound to original monster roster slots plus available identity fields; mismatches invalidate and replan. First-pass and replacement sequences are checked for provable card-instance, target and energy violations. Unknown intents no longer automatically reject every replacement; provable Block regression with unresolved intents is protected. New C2 reflection trajectories receive bounded verifier/controller attribution evidence without modifying the shared historical reflection prompt.

**v1.6.1 (Run 49 onward).** Retains exact enemy targets but permits equivalent card copies, and rejects unsupported zero-energy Whirlwind substitutions. New C2 reflection provenance includes v1.6.1 events. Source and offline tests do not establish a live improvement.

## Historical Run 48 local cutover requirements

1. Stop the game/controller and verify Run 47 FINALIZED, a Run-47 POST_RUN_REFLECTION_COMPLETE event and playbook updated through at least Run 47.
2. Preserve local uncommitted experimental evidence before safely pulling master.
3. Run python .\spirecomm\freeze_c2_run47_checkpoint.py; verify the write-once ZIP in spirecomm/runs/_local_checkpoints/.
4. Run the offline regressions and launch the current spirecomm/test_connection.py only after they pass.
5. Confirm the first new RUN_START is at Ascension 10 and records the v1.6 controller_variant.

See [current Run-48 setup](RUN48_CONTROLLER_V16.md), [historical v1.5 design](RUN43_ACTIVE_SUPERSESSION.md), [controller provenance](CONTROLLER_HISTORY.md), and [logging fields](LOGGING_SCHEMA.md).

**Current Run-49 procedure:** [v1.6.1 guide](RUN49_CONTROLLER_V161.md). Preserve both the earlier Run-47 and new Run-48 write-once local checkpoints.
