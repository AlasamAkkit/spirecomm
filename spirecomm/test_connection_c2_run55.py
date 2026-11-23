"""Run-55+ v1.7: safer structured choices and context-selected human memory.

This is a versioned intervention after the frozen, locally finalized Run 54.
All v1.6.1 combat execution, action feasibility, X-cost and targeting checks
remain inherited. No prior run, original human teaching, or raw-memory file is
rewritten. v1.7 changes what is PROMPTED, not what is retained in memory.

CommunicationMod should launch test_connection.py, not this file separately.
"""
from __future__ import annotations

import json
from pathlib import Path

import test_connection_c2_run49 as v161
from run55_policy import (
    MAX_CONTEXT_RULES, format_selected_rules, parse_json_object, select_rules,
)

base = v161.base
INTERVENTION_START_RUN = 55
VARIANT = "c2-v1.7.0-run55-context-memory-json-safety+a10"
MEMORY_POLICY = "v17-context-ranked-authoritative-entity-pinning"
CHECKPOINT_FILE = (
    Path(__file__).resolve().parent / "runs" / "_local_checkpoints" /
    "C2_through_run54_pre_v1_7.zip"
)

# Surgical parser improvement: the historical v1.2 card evaluator and v1.3
# combat verifier each hold a reference to the older strict JSON parser.
# Replace only those references in this process, without editing old modules.
v12 = v161.run48.run43.a10.stable.v131.v130.v121.v120
v13 = v161.run48.run43.a10.stable.v131.v130
v12._clean_json_object = parse_json_object
v13._clean_json_object = parse_json_object

# The v1.6.1 logger owns controller_variant. Update its process-local label
# so all actual ACTION/RUN_START/LLM events identify v1.7 correctly.
v161.VARIANT = VARIANT


def verify_run54_cutover(events_file, playbook_file, review_file, checkpoint):
    """Fail closed until the exact local Run-54 learning boundary is frozen."""
    if not Path(checkpoint).is_file():
        raise ValueError(
            "Run-54 write-once checkpoint missing. With STS stopped, run "
            "python spirecomm/freeze_c2_run54_checkpoint.py"
        )
    packet = json.loads(Path(review_file).read_text(encoding="utf-8"))
    if packet.get("status") != "FINALIZED" or int(packet.get("source_run") or 0) != 54:
        raise ValueError("Run 54 human review has not been FINALIZED.")
    decision = packet.get("review_decision")
    if decision not in {"HUMAN_TEACHING", "APPROVE_INITIAL"}:
        raise ValueError("Run 54 review decision missing or unsupported.")
    if decision == "HUMAN_TEACHING" and not str(packet.get("human_feedback") or "").strip():
        raise ValueError("Run 54 human teaching is empty.")
    playbook = json.loads(Path(playbook_file).read_text(encoding="utf-8"))
    if int(playbook.get("updated_through_run") or 0) < 54:
        raise ValueError("Run 54 learning has not entered the live playbook.")
    completed = False
    with Path(events_file).open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            event = json.loads(line)
            if (event.get("event_type") == "POST_RUN_REFLECTION_COMPLETE"
                    and event.get("completed_run_number") == 54
                    and event.get("reflected_run_id") == packet.get("source_run_id")):
                completed = True
    if not completed:
        raise ValueError("Run 54 matching POST_RUN_REFLECTION_COMPLETE not found.")
    return playbook


class ContinualC2Run55Agent(v161.ContinualC2Run49Agent):
    def __init__(self, *args, **kwargs):
        verify_run54_cutover(
            base.EVENTS_FILE, base.PLAYBOOK_FILE,
            Path(__file__).resolve().parent.parent / "reflection" /
            "condition_c2_outputs" / "run_54_feedback_review.json",
            CHECKPOINT_FILE,
        )
        super().__init__(*args, **kwargs)
        if self.completed_run_count < 54:
            raise ValueError("v1.7 requires at least 54 completed runs.")
        self.log_debug(
            f"RUN55_V17_READY: next_run={self.completed_run_count + 1}, "
            f"context_memory_soft_limit={MAX_CONTEXT_RULES}; "
            "v1.6.1 gameplay safety gates retained."
        )

    def log_run_event(self, event_type, game_state=None, **details):
        # The inherited v1.3 retrieval logs all candidate rules. Rename
        # that audit event so it does not falsely claim all were prompted.
        if (event_type == "MEMORY_RETRIEVAL"
                and details.get("memory_policy") == "all_applicable_rules_no_topk_with_context_pinning_v1"):
            event_type = "RUN55_MEMORY_CANDIDATES"
        details.setdefault("run55_intervention_start_run", INTERVENTION_START_RUN)
        details.setdefault("run55_memory_policy", MEMORY_POLICY)
        result = super().log_run_event(event_type, game_state, **details)

        # v1.2 silently chose Skip when its LLM produced invalid structured
        # scores. Log the problem and pause BEFORE returning any action.
        if (event_type == "LLM_CALL"
                and details.get("decision_type") == "CARD_REWARD_EVALUATION_V12"
                and details.get("fallback_used")):
            error = str(details.get("parse_error") or "Invalid card reward scores")
            super().log_run_event(
                "RUN55_CARD_REWARD_PARSE_PAUSED", game_state,
                run55_intervention_start_run=INTERVENTION_START_RUN,
                parse_error=error,
                raw_answer=details.get("raw_answer"),
                reason="No irreversible card reward action was issued.",
            )
            raise base.ExperimentPausedError(
                reason="card_reward_structured_parse_failure",
                decision_type="CARD_REWARD_EVALUATION_V12",
                error_type="StructuredResponseError",
                error_message=error,
            )
        return result

    def add_memory_to_prompt(
        self, decision_type, prompt, game_state=None,
        memory_category=None, output_instruction="Return ONLY the number.",
    ):
        # Preserve ALL inherited fixed safety text (Frail/Block projection,
        # Run-48 unknown-intent warning, Run-49 Whirlwind guard and v1.4
        # fixed execution checks) and only replace v1.3's verbose memory span.
        if decision_type in {"COMBAT_PLAN_VERIFIER_V13", "COMBAT_STICKY_TURN_PLAN_V12"}:
            prompt += (
                "\nV1.7 CONDITIONAL TEACHING: An old setup/card-order preference is "
                "not automatically superior to an already executable lethal line "
                "or concrete survival. For UNKNOWN/DEBUG enemy intents, missing "
                "attack damage is uncertain, not zero; do not claim zero expected "
                "loss without evidence. Only change a valid plan for a demonstrated "
                "improvement; never claim unsupported lethal or safety."
            )

        augmented, category, _legacy_ids = super().add_memory_to_prompt(
            decision_type, prompt, game_state=game_state,
            memory_category=memory_category,
            output_instruction=output_instruction,
        )
        candidates = list(self.retrieve_memories(category))
        selected, audit = select_rules(candidates, category, game_state)
        selected_ids = audit["selected_ids"]
        if candidates:
            starts = [
                augmented.find("\n\nSTATE-MATCHED AUTHORITATIVE HUMAN TEACHING"),
                augmented.find("\n\nCUMULATIVE LEARNED POLICY — ALL APPLICABLE RULES:"),
            ]
            starts = [n for n in starts if n >= 0]
            start = min(starts) if starts else -1
            end = augmented.find("\n\nDECISION AUTHORITY ORDER (highest to lowest):", start)
            if start < 0 or end < 0 or end <= start:
                raise ValueError(
                    "v1.7 could not locate inherited cumulative memory block; "
                    "refusing to send an unverified prompt."
                )
            augmented = (
                augmented[:start]
                + "\n\n" + format_selected_rules(selected)
                + augmented[end:]
            )

        self.log_run_event(
            "MEMORY_RETRIEVAL", game_state,
            decision_type=decision_type,
            memory_category=category,
            memory_policy=MEMORY_POLICY,
            memory_ids=selected_ids,
            memory_count=len(selected),
            candidate_memory_count=audit["candidate_count"],
            omitted_memory_count=audit["omitted_count"],
            omitted_memory_ids=audit["omitted_ids"],
            pinned_authoritative_rule_ids=audit["pinned_authoritative_ids"],
            soft_limit_exceeded=audit["soft_limit_exceeded"],
            state_entities=audit["entity_names"],
            prompt_characters_after_selection=len(augmented),
            playbook_updated_through_run=self.playbook.get("updated_through_run"),
            memory_file=str(base.MEMORY_FILE),
            playbook_file=str(base.PLAYBOOK_FILE),
        )
        return augmented, category, selected_ids


# Historical modules chain into the frozen CommunicationMod main() using this
# single binding. The v1.6.1 class is still available for A/B comparison.
base.STSAgent = ContinualC2Run55Agent


def main():
    v161.main()


if __name__ == "__main__":
    main()
