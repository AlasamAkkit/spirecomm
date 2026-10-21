# C2 A10 transition and active human review (proposed Run 39 boundary)

**Status:** Implementation is staged on a review branch. It is NOT deployed in
the user's local game and has NOT been verified against a live A10 run.

## Immutable history

- Runs 1–36: historical C2 controller interventions / checkpoint.
- Run 37: A0 win, first successful Act 3 clear.
- Run 38: A1 loss, Act 2 Floor 21, score 184; completed RUN_END, feedback pending
  at time this implementation was drafted.
- Run 39 onward: fixed Ascension 10 STRESS TEST after Run 38 is reviewed.
- Highest **actually cleared** Ascension is derived from genuine WIN events;
  an A10 policy override must not be represented as an A1–A9 clearance.
- The previous matched B2 vs C2 datasets remain frozen and out of scope.

## One-time safe cutover

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
4. Install this review branch only when its contents have been validated and
   your local tracked-file changes have been safely backed up. This branch
   replaces the stale GitHub `spirecomm/test_connection.py` with a minimal
   active entry point. Do not run `activate_c2_stable.py` again; that script
   was only for the historical Run-36 to Run-37 transition.
5. Finalize the historical run **without launching a game**:

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
