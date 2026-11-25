"""Optional C2 v1.7.3: strict schema for PERMANENT card rewards only.

The active test_connection.py remains on v1.7.2. To select this experimental
intervention explicitly, launch test_connection_v173_optin.py instead, after
a finalized/reflected Run 57+ boundary. Historic controller files are untouched.
"""
from __future__ import annotations

import json
from pathlib import Path

import test_connection_c2_v172 as v172
from run57_reliability_policy import legal_action_count
from run58_structured_output_policy import (
    FORMAT_NAME, LABEL, _ClientWithCardSchema, card_reward_text_format,
)

base = v172.base
VARIANT = "c2-v1.7.3-strict-card-reward-optin+a10"
RUN57_REVIEW = (
    Path(__file__).resolve().parent.parent / "reflection" /
    "condition_c2_outputs" / "run_57_feedback_review.json"
)


def verify_run57_cutover(events_file, playbook_file, review_file) -> None:
    """Read-only gate: don't start a new policy before Run 57 is finalized."""
    review = json.loads(Path(review_file).read_text(encoding="utf-8"))
    if (review.get("status") != "FINALIZED"
            or review.get("source_run") != 57
            or review.get("review_decision") not in
            {"APPROVE_INITIAL", "HUMAN_TEACHING"}):
        raise ValueError("Optional v1.7.3 requires finalized Run-57 review.")
    if (review.get("review_decision") == "HUMAN_TEACHING"
            and not str(review.get("human_feedback") or "").strip()):
        raise ValueError("Run-57 HUMAN_TEACHING review has empty feedback.")
    run_id = str(review.get("source_run_id") or "")
    if not run_id:
        raise ValueError("Run-57 review is missing source_run_id.")

    playbook = json.loads(Path(playbook_file).read_text(encoding="utf-8"))
    if int(playbook.get("updated_through_run") or 0) < 57:
        raise ValueError("Run-57 feedback is not yet in the live playbook.")

    ended = reflected = False
    with Path(events_file).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid event JSON at line {line_number}"
                ) from exc
            if event.get("completed_run_number") != 57:
                continue
            if (event.get("event_type") == "RUN_END"
                    and event.get("run_id") == run_id):
                ended = True
            if (event.get("event_type") == "POST_RUN_REFLECTION_COMPLETE"
                    and event.get("reflected_run_id") == run_id):
                reflected = True
    if not ended or not reflected:
        raise ValueError(
            "Run-57 RUN_END and matching POST_RUN_REFLECTION_COMPLETE "
            "are required before enabling the new request format."
        )


class ContinualC2V173Agent(v172.ContinualC2V172Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.completed_run_count < 57:
            raise ValueError("v1.7.3 requires at least 57 completed C2 runs.")
        self.log_debug(
            "C2_V173_OPTIN_READY: next_run=" +
            str(self.completed_run_count + 1) +
            "; structured_output_scope=permanent_card_rewards_only"
        )

    def call_llm(self, label, prompt, game_state=None, effort="low"):
        # Unchanged inherited path for index-only, combat, shops, events, etc.
        if label != LABEL:
            return super().call_llm(
                label, prompt, game_state=game_state, effort=effort
            )

        try:
            count = legal_action_count(prompt)
        except ValueError:
            # v1.7.2 already fails closed with its own pause event; do not
            # silently send an unstructured API request or select Skip.
            return super().call_llm(
                label, prompt, game_state=game_state, effort=effort
            )
        format_spec = card_reward_text_format(count)
        if self.client is None:
            raise ValueError("Structured card reward called without an API client")

        # Restrict schema injection to this one synchronous nested call.
        # v1.7.2 still owns malformed-response validation and up to 3
        # response retries; inherited base still owns bounded API retries.
        # Original response.output_text and model-score logs are preserved.
        original_client = self.client
        self.client = _ClientWithCardSchema(original_client, format_spec)
        try:
            self.log_run_event(
                "RUN58_STRUCTURED_CARD_REWARD_REQUEST",
                game_state,
                decision_type=label,
                requested_schema=FORMAT_NAME,
                legal_action_count=count,
                schema_strict=True,
                experimental_policy=VARIANT,
                transport_retry_policy="inherited",
                card_reward_validation_policy="v1.7.2",
            )
            return super().call_llm(
                label, prompt, game_state=game_state, effort=effort
            )
        finally:
            # Never apply the card schema to subsequent non-card decisions.
            self.client = original_client


def main():
    """Explicit opt-in only; does NOT run on normal test_connection.py."""
    verify_run57_cutover(base.EVENTS_FILE, base.PLAYBOOK_FILE, RUN57_REVIEW)
    # Process-local rebinding only once the operator explicitly selects
    # the opt-in launcher and all finalized experiment prerequisites pass.
    base.STSAgent = ContinualC2V173Agent
    v172.v171.v17.v161.VARIANT = VARIANT
    return v172.main()


if __name__ == "__main__":
    main()
