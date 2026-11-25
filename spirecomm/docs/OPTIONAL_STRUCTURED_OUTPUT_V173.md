# Optional v1.7.3 — strict Structured Outputs for permanent card rewards

**Status:** Implemented and offline-testable. **Not active by default.**
This is a distinct optional controller intervention. The normal
CommunicationMod entry point, spirecomm/test_connection.py, **still starts
v1.7.2**. No frozen controller, experiment files, or human feedback were changed.

API guide: https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses

## Problem and improvement

Runs 54 and 57 exposed LLM formatting defects in JSON card-reward responses.
v1.7.2 repairs narrow classes, validates, retries three times, and pauses
instead of silently choosing Skip when recovery is not possible.

The optional v1.7.3 layer sends a strict JSON Schema with the Responses API's
text.format for CARD_REWARD_EVALUATION_V12.

The exact numeric-string score keys are derived from the numbered LEGAL ACTIONS
section (2–20 legal options). The required deck plan, boolean plan_changed,
explanations and complete scores mapping are enforced by the schema; no
extra fields are allowed.

**The existing v1.7.2 validation remains**: scores must be finite JSON
numbers within 0–100, explanations must be nonempty, and actions legal.
Invalid schema responses, incomplete outputs, refusals, and API errors
never trigger an unstructured fallback or automatic Skip. The inherited
retry/pause mechanism remains authoritative.

## Scope intentionally unchanged

- Combat decisions, planning, verifier prompts and safety checks.
- Human feedback, raw memory, playbook, retrieval and expert priors.
- Post-run reflection, metadata generation, and human-teaching policy.
- Deck strategy, score semantics, selection argmax/tie policy.
- Run numbering, RNG seed schedule, historical controllers, checkpoints.
- The active test_connection.py launcher and historical v1.7.2 code.

Strict formatting does NOT imply strategically correct scores. Treat v1.7.3
as a new intervention when comparing the results of experiments.

## Offline regression checks (no API/game calls)

From the repository root (containing spirecomm/ and reflection/):

    & .\spirecomm\venv\Scripts\python.exe .\spirecomm\test_c2_v172_preflight.py
    & .\spirecomm\venv\Scripts\python.exe .\spirecomm\test_c2_v173_preflight.py

CI runs these checks automatically.

## Optional activation only after a clean experiment boundary

1. Stop the game and Python controller. Never change the launcher during
   an active or incomplete run.
2. Finalize Run 57 in the review app and verify the matching RUN_END,
   POST_RUN_REFLECTION_COMPLETE and playbook updated through at least Run 57.
   The v1.7.3 opt-in launcher checks this boundary and refuses to start early.
   If reflection processing is pending, the existing
   spirecomm/finalize_pending_review.py --run 57 tool can complete it while
   the game is closed, but this is a state-changing recovery utility. Only
   run it when its stated preconditions hold and the review is finalized.
3. Preserve your pre-intervention research evidence locally. Do not commit
   private checkpoints, raw memories or run logs.
4. With the controller stopped, pull the repository changes and run the
   offline tests above.
5. In CommunicationMod's configuration command, change **only the script
   filename** from test_connection.py to test_connection_v173_optin.py,
   keeping the same absolute script directory and Python interpreter.
   Keep runAtGameStart=true and the configured initialization timeout.
6. Launch ModTheSpire normally. Look for C2_V173_OPTIN_READY and, at a
   permanent card reward, RUN58_STRUCTURED_CARD_REWARD_REQUEST. Actual run
   events should identify controller_variant as
   c2-v1.7.3-strict-card-reward-optin+a10.

If Run 58 has already started under v1.7.2, finish and review it before
switching. The first v1.7.3 run may therefore be later than Run 58.

### Rollback

Close the game and controller, then set the CommunicationMod command back
to test_connection.py. Do not modify memories, checkpoints, seed schedule,
or run counts. If any attempt was interrupted, preserve its evidence and
do not silently treat it as a completed game.

## Model/SDK compatibility and evaluation limits

The same existing MODEL and installed openai SDK are used. Offline checks
cannot establish account/model support; **no live API call was made** as
part of implementation. If an API rejects the schema, existing bounded
retries pause the experiment rather than switching model or using
unconstrained generation.

Strict JSON Schema supports required fields/types/enum and exact indices.
Application-side v1.7.2 validation continues enforcing score ranges and
nonempty explanations. Measure retry rate, format failure rate, token
consumption, response latency, and downstream gameplay results separately.

## Files and audit

- spirecomm/run58_structured_output_policy.py: schema and response-envelope
  validation; no gameplay logic.
- spirecomm/test_connection_c2_v173.py: optional subclass; restores the
  original API client immediately after card-reward model calls.
- spirecomm/test_connection_v173_optin.py: explicit optional launcher.
- spirecomm/test_c2_v173_preflight.py: offline tests.
- spirecomm/test_connection.py: **unchanged** (still v1.7.2).

RUN58_STRUCTURED_CARD_REWARD_REQUEST is an event name for the initial
intended cutover, not a claim about the current run number.
