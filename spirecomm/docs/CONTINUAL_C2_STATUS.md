# Continual C2 Status

> **Current documentation as of 2026-11-02:** Runs 37–47 have been reviewed in the conversation; the user reports Run 47 finalized. The repository's active **code** is v1.6 for Run 48+, but a Run-48 live execution is **not verified**. The local live ledger, feedback and playbook are the authority for finalized status; do not infer local checkpoint creation from a GitHub commit.

## Current controller and operational state

| Item | Current state |
|---|---|
| Active launcher | spirecomm/test_connection.py → test_connection_c2_run48.py |
| Controller marker | c2-v1.6.0-run48-target-identity-plan-feasibility+a10 |
| Difficulty | Fixed Ascension 10 since Run 39 |
| Most recent user-reported review | Run 47 FINALIZED; local event/playbook must still be verified on the game machine |
| First run intended for v1.6 | Run 48 (not yet verified live) |
| Local safety prerequisite | Write-once C2_through_run47_pre_v1_6.zip via freeze_c2_run47_checkpoint.py |
| Offline testing | GitHub regression checks have passed; no claim of end-to-end CommunicationMod gameplay verification |

## Controlled B2/C2 result (frozen)

| Metric | B2 autonomous | C2 human-taught |
|---|---:|---:|
| Runs | 15 | 15 |
| Wins | 0 | 0 |
| Mean floor | 18.73 | **27.33** |
| Median floor | 16 | **23** |
| Best floor | 29 | **50** |
| Mean score | 144.60 | **251.47** |
| Act 2+ | 6/15 | **13/15** |
| Act 3 | 0/15 | **2/15** |

Same 15 seeds and frozen controllers; C2 higher floor on 11/15 and score on 10/15. **Never pool continual A10 episodes into the controlled result.**

## Continual phase boundaries

| Run range | Controller | Main engineering boundary |
|---|---|---|
| 16–28 | v1.0 | Continual memory and seeds |
| 29–32 | v1.1.1 | Card priors and turn proposals |
| 33 | v1.2.0 | Sticky turn plans and persistent deck plan |
| 34 | v1.2.1 | Applicable-authority ranking hotfix |
| 35 | v1.3.0 | All-applicable memory + verifier |
| 36 | v1.3.1 | Frail/Dex Block projection |
| 37–38 | v1.4 | Encounter-safe sticky plans; early stable phase |
| 39–42 | v1.4 + A10 | Fixed Ascension 10 with original v1.4 gameplay |
| 43–47 | v1.5 + A10 | Human supersession at Neow and conservative verifier guards |
| 48+ | v1.6 + A10 | Target binding, plan-feasibility checks, scoped unknown-intent safeguard and reflection attribution; live run pending |

See [Runs 37–48 evidence ledger](RUNS_39_48_A10_EVALUATION.md) for per-run floor outcomes and careful limitations.

## Correct operating procedure

1. Close the game/controller. Confirm the Run-47 review and POST_RUN_REFLECTION_COMPLETE locally and playbook.updated_through_run >= 47.
2. Preserve local changes and pull updated master safely.
3. Run the new freeze_c2_run47_checkpoint.py once; it refuses to overwrite an existing archive.
4. Run stable, A10, Run-43, Run-48 and reflection regression checks.
5. Launch the same normal CommunicationMod flow. Verify the Run-48 RUN_START marker and Ascension 10.
6. For future completed runs: RUN_END → initial reflection → human review → raw memory/playbook update → POST_RUN_REFLECTION_COMPLETE. Do **not** change the controller after every loss.

Review UI: python reflection/feedback_app.py --output-dir reflection/condition_c2_outputs.

## Interpretation

- Learning is persistent **external memory**. The underlying model weights are not updated.
- A retrieved lesson proves **availability**, not actual behavioral compliance.
- Verifier approval is not deterministic proof of a legal, optimal or lethal action.
- The v1.6 guards detect certain provably infeasible plans and protect target identity; they are **not** a complete game simulator.
- Runs across v1.4/v1.5/v1.6 have different controller mechanics and independent seeds. Report them as separate descriptive intervention phases.
- Do not rewrite earlier collected events to align with the latest interpretation.

## Primary references

- [Run 48 activation and regression protocol](RUN48_CONTROLLER_V16.md)
- [A10 longitudinal ledger](RUNS_39_48_A10_EVALUATION.md)
- [Controller history](CONTROLLER_HISTORY.md)
- [Human-feedback mechanism](HUMAN_FEEDBACK_MECHANISM.md)
- [Logging schema](LOGGING_SCHEMA.md)
