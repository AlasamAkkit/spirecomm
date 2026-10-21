# C2 A10 transition and active human review (proposed Run 39 boundary)

**Status (2026-10-21):** Implementation has been merged into `master`.
The post-merge conflict in `spirecomm/test_connection.py` was fixed by
restoring the minimal A10 launcher; GitHub Actions compile, stable-v1.4
preflight, A10 policy and offline review tests now pass. The user confirmed
their **local** cumulative playbook was updated through Run 38. This does
not independently verify an A10 game launch; Run 39 must still be checked
against its actual `RUN_START` record.

## Immutable history

- Runs 1–36: historical C2 controller interventions / checkpoint.
- Run 37: A0 win, first successful Act 3 clear.
- Run 38: A1 loss, Act 2 Floor 21, score 184; feedback reported processed
  locally by the user on 2026-10-21. The tracked pre-finalization
  snapshot still intentionally shows the BEFORE state (playbook through 37).
- Run 39 onward: fixed Ascension 10 STRESS TEST after Run 38 is reviewed.
- Highest **actually cleared** Ascension is derived from genuine WIN events;
  an A10 policy override must not be represented as an A1–A9 clearance.
- The previous matched B2 vs C2 datasets remain frozen and out of scope.

## One-time safe cutover (historical steps 1-5 completed locally)

1. **Stop Slay the Spire/CommunicationMod controller before finalizing feedback.**
   The current controller will otherwise start the next run when the feedback
   packet is submitted.
2. Back up live data before checking out this branch:
   `spirecomm/run_events_c2.jsonl`, `spirecomm/sts_messages.log`,
   `reflection/condition_c2_raw_memory.jsonl`,
   `reflection/condition_c2_playbook.json`,
   `reflection/condition_c2_feedback.jsonl`,
   `reflection/condition_c2_outputs/`,
   `spirecomm/c2_continual_seed_schedule.json` and
   `spirecomm/c2_continual_progress.json`.
   **Do not reset, erase, or fabricate event logs.**
3. Use the **existing** local feedback UI to finish Run 38 with the appropriate
   `HUMAN_TEACHING` or `APPROVE_INITIAL`. The feedback server may be running,
   but the gameplay/controller process must be stopped.
4. The A10 code is now merged into `master`. Update the local `master`
   only after protecting any local working changes:
   `git status --short`, then `git pull --ff-only origin master`.
   Verify `spirecomm/test_connection.py` is the **minimal A10 launcher**,
   not a pasted copy of the stable controller. Do not run
   `activate_c2_stable.py` again; that script belongs to Run 36.
5. If Run 38 has **not yet been reflected**, finalize it **without launching
   a game**. If the local playbook already reports
   `updated_through_run=38` and the event log contains
   `POST_RUN_REFLECTION_COMPLETE` for Run 38, this step is complete:

   ```powershell
   python .\spirecomm\finalize_pending_review.py --run 38
   ```

   The tool refuses to proceed if Run 39 already has a `RUN_START`. It saves
   a local pre-A10 snapshot, processes the pending reflection, and verifies
   `POST_RUN_REFLECTION_COMPLETE` plus playbook `updated_through_run=38`.
   It never calls the CommunicationMod gameplay loop.

6. Run quick static/regression checks before resuming:

   ```powershell
   python -m py_compile .\spirecomm\test_connection.py .\spirecomm\test_connection_c2_a10.py .\spirecomm\finalize_pending_review.py .\reflection\active_review.py .\reflection\feedback_app.py .\reflection\followup_reflection.py
   python .\spirecomm\test_c2_stable_preflight.py
   python -m unittest discover -s .\reflection\tests -p "test_*.py"
   python .\spirecomm\test_c2_a10_policy.py
   ```

   If any fail, **do not start Run 39**; restore from the preserved snapshot
   or debug the review branch without modifying the original run evidence.

7. Use the normal feedback server, then launch the game/agent as before:

   ```powershell
   python .\reflection\feedback_app.py --output-dir reflection/condition_c2_outputs
   ```

   On the next `RUN_START`, verify `ascension=10`,
   `active_ascension=10`, `difficulty_policy=fixed-a10-from-run39-v1`.
   Retain controller lineage and full raw memory.

## Why the tracked Run-38 snapshot does not say through 38

`spirecomm/runs/C2_through_run38_pre_A10/` was intentionally created
**before Run 38's pending feedback was incorporated**. Therefore its
playbook has `updated_through_run=37`. This is correct for that
pre-finalization checkpoint and must not be overwritten or treated as
the active memory bank. The latest local
`reflection/condition_c2_playbook.json` and the run event log are the
source of truth after finalization. Keep both backed up.

The tracked `spirecomm/c2_continual_progress.json` may also still say
Ascension 1. It is a derived runtime cache, reconstructed from the event
log by the A10 wrapper when the new controller initializes. Do not
manually edit past `RUN_END` or `clearances` to make the jump to A10.

## Review system: what changed and what did not

**Unchanged:**
- A run must finish before the human review.
- `APPROVE_INITIAL` approves the LLM's initial up-to-3 lessons unchanged.
- `HUMAN_TEACHING` stores the general human teaching **verbatim** with
  metadata-only classification, as before.
- All previous human lessons remain in the cumulative playbook.

**New optional review assistance, for packets generated after this upgrade:**
- Deterministic *suspected* issues: significant observed HP loss, unspent gold
  with no recorded shop purchase, verifier interventions. Flags are hypotheses.
- A separate post-run LLM reviewer asks at most three grounded, trace-linked
  questions about consequential decisions. This is **retrospective uncertainty
  identification**, not real-time introspection by the acting LLM.
- The UI presents exact action, floor, alternatives, uncertainty and
  assumption-to-verify so a human can review evidence.
- Each question can be left unreviewed, confirmed, dismissed, or corrected.
  **Only** explicit `CORRECT` with nonempty human teaching becomes an
  additional authoritative lesson. Its exact text is preserved separately,
  linked by question ID and run, and classified for the ordinary playbook.
- The existing general teaching and question-level corrections can coexist.

The optional question-generation call is best effort. If it fails, it is
recorded and the original feedback process remains available. Existing Run 38
review packets are read as-is; they do not retroactively gain questions.
No model-proposed mistake becomes authoritative without human correction.

## Research boundaries

1. **Run 39 is an environment-difficulty intervention**. Do not compare A10
   runs to the A0 matched seeds as if difficulty and controller were fixed.
2. The first runs at A10 can be pilot runs before measuring the feedback
   enhancement's effect. If rigorous attribution is required, snapshot a
   memory state and run matched-seed feedback variants separately.
3. The added post-run diagnostic/question UI changes feedback acquisition but
   not live combat prompts. Verbal teaching remains the only authoritative
   source of corrections.
4. Model uncertainty reported post-run is a hypothesis, and may miss confident
   mistakes. The reviewer must validate it against evidence.

## Working tree map

| Active / supported | Purpose |
|---|---|
| `spirecomm/test_connection.py` | Single minimal gameplay entry point |
| `spirecomm/test_connection_c2_a10.py` | Explicit A10 policy from Run 39 |
| `spirecomm/test_connection_c2_stable.py` | Frozen gameplay controller v1.4 |
| `spirecomm/finalize_pending_review.py` | One-shot review finalization without gameplay |
| `reflection/feedback_app.py` | The same browser UI, extended with optional questions |
| `reflection/followup_reflection.py` | Raw-memory/playbook/feedback pipeline |
| `reflection/active_review.py` | Additional evidence and post-run question generator |
| `reflection/condition_c2_*.json*` | Local LIVE state; do not treat tracked examples as authoritative |
| `spirecomm/runs/` | Frozen controlled and historical experiment evidence |
| `spirecomm/test_connection_c2_continual_v1*.py` | Historical controllers required by the dynamic import chain |

### Cleanup policy

Historical controller wrappers cannot simply be deleted or moved: v1.4
imports v1.3.1 and its ancestry by exact path. Historical finalizer/freezer
scripts are not used during an ordinary run but should remain available for
research reproduction. Keep the active entry points few, and document the
rest as immutable history. Do not commit live credentials, human-feedback
secrets, giant working JSONL logs, or reconstructed logs.
