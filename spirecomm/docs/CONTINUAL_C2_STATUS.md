# Continual C2 Status

> **As of the Run-37 start (October 2026):** Run 36 is the most recent **finalized/reflected** run.  
> **Run 37:** reported in progress, no verified result yet.  
> **Ascension:** 0 at the Run-36 checkpoint.  
> **Active local controller:** `c2-continual-teaching-v1.4.0-stable-feedback-loop` (one-time activation passed).  
> **Baseline:** 36 completed/reflected runs, 50 raw lessons, 36 playbook rules, 36 feedback rows.

This is the concise *current* status page. Earlier through-Run-33 status and detailed change history are retained in the ledger, changelogs, controller history and checkpoints.

## Controlled comparison (complete and frozen)

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

On matched seeds, C2 reached a higher floor in 11/15 and a higher score in 10/15. The matched Phase II analysis remains frozen; do not append continual-run data to those tables.

## Continual phase and engineering boundaries

| Runs | Controller | Key change | Finalized evidence |
|---|---|---|---|
| 16–28 | v1.0 | Open-ended memory and independent seed/Ascension state | Checkpoint through 28 |
| 29–32 | v1.1.1 | Card priors + turn-plan proposal without persistent action execution | Run-32 checkpoint: 46 lessons / 32 rules |
| 33 | v1.2.0 | Sticky multi-action combat and persistent deck plan; focused top-k | LOSS Act 2/F33, 292 |
| 34 | v1.2.1 | Applicable-authority recency ranking hotfix | LOSS Act 2/F22, 194; checkpoint: 48 lessons / 34 rules |
| 35 | v1.3.0 | **All-applicable cumulative retrieval** and independent plan verifier | LOSS Act 2/F33, 273; checkpoint: 49 lessons / 35 rules |
| 36 | v1.3.1 | Known Frail/Dexterity-adjusted Block projection and audit | LOSS Act 2/F23, 193; finalized: 50 lessons / 36 rules |
| **37+** | **v1.4.0** | Cross-encounter plan reset, queued End-turn recheck, fixed-code evaluation | Run 37 in progress at last report |

The local `activate_c2_stable.py` command reported **C2 STABLE ACTIVATION: PASS** and **10/10 regression tests passed**. It also created `spirecomm/runs/C2_continual_through_run36_pre_stable/` locally; do not assume that snapshot has been pushed to GitHub until committed.

## Why the interventions happened

1. **Runs 16–28:** accumulated advice did not solve reward/build and action-ordering weaknesses.
2. **Runs 29–32:** a planned full turn was thrown away after the first action; tactical replanning could abandon previously selected Block.
3. **Run 33:** sticky planning helped execution, but focused top-k memory misranked a newer cross-category human lesson.
4. **Run 34:** a ranking fix was insufficient because older authoritative teaching (including Run-13 Centurion/Mystic targeting) still fell outside the top-k cutoff.
5. **Run 35:** full retrieval and verifier operated, but it predicted 49 printed Block against Collector while actual Frail-adjusted Block was 36.
6. **Run 36:** deterministic Block projection ran; a queued `End turn` could persist from a previous encounter because the legacy sticky guard checked run + turn, not encounter identity. Strategic problems such as prolonged combat and low-HP shop choices remained.
7. **Run 37:** v1.4.0 hardens the executor at that boundary, then is intentionally frozen for evaluating human teaching rather than iteratively rewritten after each loss.

See [SYSTEM_ARCHITECTURE_AND_RETROSPECTIVE.md](SYSTEM_ARCHITECTURE_AND_RETROSPECTIVE.md) for code-level diagnosis, evidence and limitations; [CONTINUAL_RUN_LEDGER_33_37.md](CONTINUAL_RUN_LEDGER_33_37.md) for outcomes.

## Stable phase operating procedure

The feedback-loop code is now intended to stay **unchanged** across Runs 37–50 (proposed evaluation window):

```text
one independently seeded run
  -> RUN_END
  -> compact trajectory + initial reflection
  -> reviewer chooses APPROVE_INITIAL or HUMAN_TEACHING
  -> final lessons, raw memory and cumulative playbook
  -> POST_RUN_REFLECTION_COMPLETE
  -> next run under same controller version
```

Do not replace `test_connection.py` between ordinary runs. Never run `activate_c2_stable.py` while a run is in progress. The feedback app is `python reflection/feedback_app.py --output-dir reflection/condition_c2_outputs` at `http://127.0.0.1:8765`.

**A run is finalized only when its `POST_RUN_REFLECTION_COMPLETE` event exists and the playbook `updated_through_run` equals that run number.** An earlier `RUN_END` alone is not enough.

## Research interpretation and limits

- The matched B2/C2 result is a controlled comparison; continual C2 is a distinct longitudinal series.
- Runs 16–36 combined feedback and code interventions; do not attribute their changes solely to teaching.
- Runs 37 onward can better isolate changes under a fixed implementation, though independent seeds still confound one-run comparisons.
- Cumulative `MEMORY_RETRIEVAL` proves teaching was **available**, not that the agent obeyed it.
- v1.3.1 Block projection and v1.4 end-turn safeguard are bounded, not a complete deterministic Slay the Spire simulator.
- Only patch frozen code for a reproducible infrastructure/validity bug; establish a new explicit intervention boundary if unavoidable.

## Quick links

- [Stable workflow](C2_STABLE_FEEDBACK_WORKFLOW.md)
- [Full system explanation and issue retrospective](SYSTEM_ARCHITECTURE_AND_RETROSPECTIVE.md)
- [Run ledger](CONTINUAL_RUN_LEDGER_33_37.md)
- [Controller history](CONTROLLER_HISTORY.md)
- [Human feedback](HUMAN_FEEDBACK_MECHANISM.md)
- [Logging schema](LOGGING_SCHEMA.md)
