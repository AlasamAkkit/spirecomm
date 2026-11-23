"""C2 v1.7.2 — Run 57 restart after a malformed card-reward response.

Do not rewrite historical Run 57 (v1.7.1) evidence. CommunicationMod keeps
launching test_connection.py, now bound to this new versioned controller.
"""
from __future__ import annotations

from pathlib import Path

import test_connection_c2_run56 as v171
from run57_reliability_policy import (
    legal_action_count, normalize_score_words, parse_card_reward_json,
    unfinished_attempt, validate_card_reward_payload,
)

base = v171.base
VARIANT = "c2-v1.7.2-run57-retry-card-reward-reliability+a10"
CARD_REWARD_RESPONSE_ATTEMPTS = 3

# The original v1.2 card evaluator resolves this parser via its module global.
# Patch only in THIS running process. Keep historic source and combat JSON
# verifier unchanged. A repaired JSON result still gets strict score checks.
v171.v17.v12._clean_json_object = parse_card_reward_json
v171.v17.v161.VARIANT = VARIANT


class ContinualC2V172Agent(v171.ContinualC2Run56Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._v172_previous_unfinished = unfinished_attempt(base.EVENTS_FILE)
        self.log_debug(
            "C2_V172_READY: next_run=" + str(self.completed_run_count + 1) +
            "; card_reward_attempts=" + str(CARD_REWARD_RESPONSE_ATTEMPTS) +
            "; unfinished_attempt=" +
            str((self._v172_previous_unfinished or {}).get("run_id"))
        )

    @staticmethod
    def _validate_scores(payload, count):
        """The inherited scorer must never accept NaN, bool or partial scores."""
        return validate_card_reward_payload(payload, count)

    def handle_state(self, state):
        if state.get("in_game") and self.current_run_id is None:
            # Restarting a Python controller into an already-running game would
            # silently misattribute events to run_id=None. Fail closed; never
            # pretend to restore the original game/run from an empty runtime.
            self.log_run_event(
                "RUN57_UNATTACHED_LIVE_GAME_PAUSED",
                state.get("game_state") or {},
                reason="No recoverable run id for already-active game",
            )
            raise base.ExperimentPausedError(
                reason="unattached_live_game_requires_explicit_recovery",
                decision_type="STARTUP",
                error_type="RunIdentityError",
                error_message="Restart game to menu or use a separately audited resume tool.",
            )

        if (not state.get("in_game")
                and state.get("ready_for_command")
                and "start" in (state.get("available_commands") or [])
                and self.current_run_id is None
                and self._v172_previous_unfinished):
            old = self._v172_previous_unfinished
            # This is a new attempt at the same *not-yet-completed* run slot.
            # Do not invent RUN_END or alter the old attempt's run_id.
            self.log_run_event(
                "RUN57_PREVIOUS_ATTEMPT_INTERRUPTED",
                state.get("game_state") or {},
                previous_run_id=old["run_id"],
                previous_requested_seed=old["requested_seed"],
                previous_pause_reason=old["reason"],
                new_run_number=self.completed_run_count + 1,
                counts_as_completed_run=False,
                message="New run attempt; previous unfinished attempt remains preserved",
            )
            self._v172_previous_unfinished = None

        return super().handle_state(state)

    def _pause_card_reward(self, game_state, reason, error_message):
        self.log_run_event(
            "RUN57_CARD_REWARD_VALIDATION_PAUSED",
            game_state,
            decision_type="CARD_REWARD_EVALUATION_V12",
            reason=reason,
            error_message=error_message,
            attempts=CARD_REWARD_RESPONSE_ATTEMPTS,
            no_gameplay_action_issued=True,
        )
        try:
            base.PAUSE_FILE.parent.mkdir(parents=True, exist_ok=True)
            base.PAUSE_FILE.write_text(
                "C2 v1.7.2 card-reward evaluation paused safely.\n"
                "Current run_id: " + str(self.current_run_id) + "\n"
                "Reason: " + reason + "\n"
                "Details: " + error_message + "\n"
                "No gameplay choice was issued. Preserve logs.\n",
                encoding="utf-8",
            )
        except OSError as exc:
            self.log_debug("RUN57_PAUSE_MARKER_WRITE_FAILED: " + str(exc))
        raise base.ExperimentPausedError(
            reason=reason,
            decision_type="CARD_REWARD_EVALUATION_V12",
            error_type="StructuredResponseError",
            error_message=error_message,
        )

    def call_llm(self, label, prompt, game_state=None, effort="low"):
        if label != "CARD_REWARD_EVALUATION_V12":
            return super().call_llm(
                label, prompt, game_state=game_state, effort=effort
            )

        try:
            expected_count = legal_action_count(prompt)
        except ValueError as exc:
            self._pause_card_reward(
                game_state, "card_reward_prompt_validation_failure", str(exc)
            )

        last_error = "no model response"
        for attempt in range(1, CARD_REWARD_RESPONSE_ATTEMPTS + 1):
            retry_prompt = prompt
            if attempt > 1:
                retry_prompt += (
                    "\n\nIMPORTANT: The preceding card-reward JSON was rejected. "
                    "ERROR: " + last_error[:350] + ". "
                    "Regenerate the FULL JSON object with the existing deck plan. "
                    "Use ONLY JSON numbers between 0 and 100 for every score; "
                    "never words (e.g. fifty), quoted scores, booleans, NaN, or "
                    "Infinity. scores must contain every action index 0 through " +
                    str(expected_count - 1) + ", and no extra indices. "
                    "Keep all required deck_plan fields and return JSON only."
                )

            # Parent owns API retries/availability pauses. A failed API request
            # must never become a card-reward fallback action.
            response, latency_ms = super().call_llm(
                label, retry_prompt, game_state=game_state, effort=effort
            )
            if response is None:
                self._pause_card_reward(
                    game_state, "card_reward_api_returned_none",
                    "Inherited API call returned None",
                )
            raw_text = str(getattr(response, "output_text", "") or "")
            try:
                payload = parse_card_reward_json(raw_text)
                scores = validate_card_reward_payload(payload, expected_count)
            except (ValueError, TypeError) as exc:
                last_error = type(exc).__name__ + ": " + str(exc)
                input_tokens, output_tokens = self.get_usage(response)
                self.log_run_event(
                    "RUN57_CARD_REWARD_INVALID_MODEL_OUTPUT",
                    game_state,
                    decision_type=label,
                    attempt=attempt,
                    max_attempts=CARD_REWARD_RESPONSE_ATTEMPTS,
                    error=last_error,
                    raw_answer=raw_text,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    no_gameplay_action_issued=True,
                )
                continue

            _, repairs = normalize_score_words(raw_text)
            if repairs:
                self.log_run_event(
                    "RUN57_CARD_REWARD_SCORE_WORD_REPAIRED",
                    game_state,
                    decision_type=label,
                    attempt=attempt,
                    repairs=repairs,
                    raw_answer=raw_text,
                    repaired_score_values={str(k): v for k, v in scores.items()},
                    normalization_scope="only_bare_words_inside_scores_object",
                    no_gameplay_action_issued_yet=True,
                )
            if attempt > 1:
                self.log_run_event(
                    "RUN57_CARD_REWARD_RESPONSE_RECOVERED",
                    game_state,
                    decision_type=label,
                    successful_attempt=attempt,
                    prior_response_was_invalid=True,
                    no_gameplay_action_issued_yet=True,
                )
            # Return the original response. The historical LLM_CALL log keeps
            # the raw model text; the patched parser produces the validated
            # structured payload without rewriting the model's original words.
            return response, latency_ms

        self._pause_card_reward(
            game_state, "card_reward_json_retries_exhausted",
            last_error,
        )


base.STSAgent = ContinualC2V172Agent


def main():
    v171.main()


if __name__ == "__main__":
    main()
