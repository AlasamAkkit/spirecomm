"""Run-49 v1.6.1 A10 controller: equivalent cards and Whirlwind X-cost guard.

Preserves all v1.6 Run-48 source and earlier human memory unchanged.
Requires local Run-48 finalization and write-once boundary checkpoint.
"""
from __future__ import annotations

import json
from pathlib import Path

import test_connection_c2_run48 as run48
from run48_policy import validate_action_sequence, unknown_intent_defense_regression
from run49_policy import (
    bind_plan_v161, find_equivalent_bound_action,
    reject_unfounded_zero_energy_whirlwind,
)

base = run48.base
INTERVENTION_START_RUN = 49
VARIANT = "c2-v1.6.1-run49-equivalent-card-xcost-guard+a10"
CHECKPOINT_FILE = (
    Path(__file__).resolve().parent / "runs" / "_local_checkpoints" /
    "C2_through_run48_pre_v1_6_1.zip"
)


def verify_run48_cutover(events_file, playbook_file, review_file, checkpoint):
    if not Path(checkpoint).is_file():
        raise ValueError(
            "Run-48 checkpoint missing. Stop STS and run "
            "python spirecomm/freeze_c2_run48_checkpoint.py before Run 49."
        )
    packet = json.loads(Path(review_file).read_text(encoding="utf-8"))
    if packet.get("status") != "FINALIZED" or int(packet.get("source_run") or 0) != 48:
        raise ValueError("Run 48 review is not FINALIZED.")
    if packet.get("review_decision") not in ("HUMAN_TEACHING", "APPROVE_INITIAL"):
        raise ValueError("Run 48 review decision missing.")
    playbook = json.loads(Path(playbook_file).read_text(encoding="utf-8"))
    if int(playbook.get("updated_through_run") or 0) < 48:
        raise ValueError("Run 48 teaching has not entered the active playbook.")
    complete = False
    with Path(events_file).open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                event = json.loads(line)
                if (event.get("event_type") == "POST_RUN_REFLECTION_COMPLETE"
                        and int(event.get("completed_run_number") or 0) == 48):
                    complete = True
                    break
    if not complete:
        raise ValueError("No Run-48 POST_RUN_REFLECTION_COMPLETE event in ledger.")
    return playbook


class ContinualC2Run49Agent(run48.ContinualC2Run48Agent):
    def __init__(self, *args, **kwargs):
        verify_run48_cutover(
            base.EVENTS_FILE, base.PLAYBOOK_FILE,
            Path(__file__).resolve().parent.parent / "reflection" /
            "condition_c2_outputs" / "run_48_feedback_review.json",
            CHECKPOINT_FILE,
        )
        super().__init__(*args, **kwargs)
        if self.completed_run_count < 48:
            raise ValueError("v1.6.1 requires completed Run 48.")

    def log_run_event(self, event_type, game_state=None, **details):
        # Reuse v1.6 feasibility, but bind more precise card-instance effect
        # information. Do not write v1.6.0 provenance on new Run-49 events.
        if (event_type == "STICKY_COMBAT_PLAN_CREATED"
                and getattr(self, "_run48_current_actions", None) is not None):
            actions = self._run48_current_actions
            indexes = details.get("action_sequence") or []
            valid, reason = validate_action_sequence(game_state, actions, indexes)
            if valid:
                bound = bind_plan_v161(game_state, actions, indexes)
                self._sticky_combat_remaining = bound[1:]
                details["planned_actions"] = bound
                details["remaining_plan"] = bound[1:]
                details["run48_target_bound"] = True
                details["run49_card_equivalence_bound"] = True
            else:
                self._clear_sticky_plan()
                details["remaining_plan"] = []
                details["run48_feasibility_rejected"] = reason
                super(run48.run43.ContinualC2Run43Agent, self).log_run_event(
                    "RUN48_FIRST_PASS_PLAN_REJECTED", game_state,
                    controller_variant=VARIANT, reason=reason,
                    proposed_action_sequence=indexes,
                    selected_first_action=details.get("selected_action"),
                    fallback="retain only legal first action; discard queued remainder",
                )
        details["controller_variant"] = VARIANT
        details["run49_intervention_start_run"] = INTERVENTION_START_RUN
        details.setdefault("run48_intervention_start_run", run48.INTERVENTION_START_RUN)
        details.setdefault("run43_intervention_start_run", run48.run43.INTERVENTION_START_RUN)
        details.setdefault("human_policy_supersession", "run23-over-run1-neow-v1")
        return super(run48.run43.ContinualC2Run43Agent, self).log_run_event(
            event_type, game_state, **details
        )

    def _try_follow_sticky_plan(self, game_state, actions):
        remaining = list(getattr(self, "_sticky_combat_remaining", []) or [])
        if not remaining:
            return None
        combat = (game_state or {}).get("combat_state") or {}
        if (self._sticky_combat_turn != combat.get("turn") or
                self._sticky_combat_run_id != str(getattr(self, "current_run_id", "") or "")):
            self._clear_sticky_with_audit(game_state, "run_or_turn_changed")
            return None
        bound = remaining[0]
        if "target_slot" not in bound and " on " in str(bound.get("signature") or ""):
            self._clear_sticky_with_audit(game_state, "unbound_target_plan_discarded")
            return None
        selected, reason, candidate_count = find_equivalent_bound_action(
            game_state, actions, bound
        )
        if selected is None:
            self._clear_sticky_with_audit(game_state, "target_binding_invalid: " + reason)
            self.log_run_event(
                "RUN49_STICKY_TARGET_REPLAN", game_state,
                expected_action=bound, reason=reason,
                candidate_count=candidate_count,
                legal_actions=[a.get("description") for a in actions],
            )
            return None
        self._sticky_combat_remaining = remaining[1:]
        if candidate_count > 1:
            self.log_run_event(
                "RUN49_EQUIVALENT_CARD_MATCH", game_state,
                expected_action=bound, candidate_count=candidate_count,
                selected_command=selected.get("command"),
                target_slot=bound.get("target_slot"),
                match_reason=reason,
            )
        self.log_run_event(
            "STICKY_COMBAT_PLAN_FOLLOWED", game_state,
            expected_action=bound["description"],
            selected_action=selected.get("description"),
            target_slot=bound.get("target_slot"),
            match_reason=reason,
            remaining_plan=self._sticky_combat_remaining,
            original_reason=getattr(self, "_sticky_combat_reason", None),
        )
        return selected

    def add_memory_to_prompt(self, decision_type, prompt, game_state=None,
                             memory_category=None,
                             output_instruction="Return ONLY the number."):
        augmented, category, ids = super().add_memory_to_prompt(
            decision_type, prompt, game_state=game_state,
            memory_category=memory_category,
            output_instruction=output_instruction,
        )
        if decision_type == "COMBAT_PLAN_VERIFIER_V13":
            combat = ((game_state or {}).get("combat_state") or {})
            hand = combat.get("hand") or []
            if any(str(card.get("name") or "").casefold().startswith("whirlwind")
                   for card in hand if isinstance(card, dict)):
                augmented += (
                    "\n\nRUN49 X-COST RULE: Whirlwind spends ALL CURRENT energy "
                    "and hits once per energy spent. At 0 energy its baseline "
                    "damage is 0 and it makes 0 hits; the relic Chemical X adds "
                    "two effective energy to X-cost effects. If you replace End "
                    "turn with a zero-energy Whirlwind for a card-play relic "
                    "trigger (such as Kunai), explicitly state that it deals "
                    "0 damage and name the concrete trigger. Never claim that "
                    "0-energy Whirlwind deals 5 damage per enemy."
                )
        return augmented, category, ids

    def _install_replacement_sticky_plan(self, game_state, actions, indexes, reason):
        original = list(getattr(self, "_run43_original_plan", None) or [])
        invalid, why = reject_unfounded_zero_energy_whirlwind(
            game_state, actions, indexes, original, reason,
        )
        if invalid:
            self.log_run_event(
                "RUN49_X_COST_REPLACEMENT_REJECTED", game_state,
                reason=why, original_plan=original,
                proposed_replacement=[actions[i].get("description") for i in indexes],
                verifier_reason=reason,
            )
            raise ValueError("Run-49 X-cost guard: " + why)
        selected, _ = super()._install_replacement_sticky_plan(
            game_state, actions, indexes, reason
        )
        bound = bind_plan_v161(game_state, actions, indexes)
        self._sticky_combat_remaining = bound[1:]
        self.log_run_event(
            "RUN49_VERIFIER_CARD_BINDING", game_state,
            bound_actions=bound, verifier_reason=reason,
        )
        return selected, bound


base.STSAgent = ContinualC2Run49Agent


def main():
    run48.main()


if __name__ == "__main__":
    main()
