"""Run-48 v1.6 A10 controller: target-stable sticky actions and plan checks.

Inherits Run-43 human supersession. Historic controllers remain untouched.
Requires a write-once, local Run-47 boundary checkpoint before launch.
"""
from __future__ import annotations

import json
from pathlib import Path

import test_connection_c2_run43 as run43
from run48_policy import (
    bind_plan, find_bound_action, validate_action_sequence,
    unknown_intent_defense_regression,
)

base = run43.base
INTERVENTION_START_RUN = 48
VARIANT = "c2-v1.6.0-run48-target-identity-plan-feasibility+a10"
CHECKPOINT_FILE = (
    Path(__file__).resolve().parent / "runs" / "_local_checkpoints" /
    "C2_through_run47_pre_v1_6.zip"
)


def verify_run47_cutover(events_file, playbook_file, review_file, checkpoint):
    if not Path(checkpoint).is_file():
        raise ValueError(
            "Run-47 offline checkpoint missing. With the game closed, run "
            "python spirecomm/freeze_c2_run47_checkpoint.py before Run 48."
        )
    packet = json.loads(Path(review_file).read_text(encoding="utf-8"))
    if packet.get("status") != "FINALIZED" or int(packet.get("source_run") or 0) != 47:
        raise ValueError("Run 47 review is not FINALIZED.")
    playbook = json.loads(Path(playbook_file).read_text(encoding="utf-8"))
    if int(playbook.get("updated_through_run") or 0) < 47:
        raise ValueError("Run 47 teaching has not entered the active playbook.")
    complete = False
    for line in Path(events_file).read_text(encoding="utf-8").splitlines():
        if line.strip():
            event = json.loads(line)
            if (event.get("event_type") == "POST_RUN_REFLECTION_COMPLETE" and
                int(event.get("completed_run_number") or 0) == 47):
                complete = True
                break
    if not complete:
        raise ValueError("No Run-47 POST_RUN_REFLECTION_COMPLETE event in ledger.")
    return playbook


class ContinualC2Run48Agent(run43.ContinualC2Run43Agent):
    def __init__(self, *args, **kwargs):
        verify_run47_cutover(
            base.EVENTS_FILE, base.PLAYBOOK_FILE,
            Path(__file__).resolve().parent.parent / "reflection" /
            "condition_c2_outputs" / "run_47_feedback_review.json",
            CHECKPOINT_FILE,
        )
        self._run48_current_actions = None
        self._run48_original_selected = None
        super().__init__(*args, **kwargs)
        if self.completed_run_count < 47:
            raise ValueError("v1.6 is only valid after completed Run 47.")

    def log_run_event(self, event_type, game_state=None, **details):
        # The first-pass planner emits this BEFORE passing the first card to
        # the verifier. Bind targets by action command, never by enemy name.
        if (event_type == "STICKY_COMBAT_PLAN_CREATED"
                and self._run48_current_actions is not None):
            actions = self._run48_current_actions
            indexes = details.get("action_sequence") or []
            valid, reason = validate_action_sequence(game_state, actions, indexes)
            if valid:
                bound = bind_plan(game_state, actions, indexes)
                self._sticky_combat_remaining = bound[1:]
                details["planned_actions"] = bound
                details["remaining_plan"] = bound[1:]
                details["run48_target_bound"] = True
            else:
                self._clear_sticky_plan()
                details["remaining_plan"] = []
                details["run48_feasibility_rejected"] = reason
                super(run43.ContinualC2Run43Agent, self).log_run_event(
                    "RUN48_FIRST_PASS_PLAN_REJECTED", game_state,
                    controller_variant=VARIANT,
                    reason=reason, proposed_action_sequence=indexes,
                    selected_first_action=details.get("selected_action"),
                    fallback="retain only legal first action; discard queued remainder",
                )
        details["controller_variant"] = VARIANT
        details.setdefault("run48_intervention_start_run", INTERVENTION_START_RUN)
        details.setdefault("run43_intervention_start_run", run43.INTERVENTION_START_RUN)
        details.setdefault("human_policy_supersession", "run23-over-run1-neow-v1")
        return super(run43.ContinualC2Run43Agent, self).log_run_event(
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
        expected = remaining[0]
        if "target_slot" not in expected and " on " in str(expected.get("signature") or ""):
            self._clear_sticky_with_audit(game_state, "unbound_target_plan_discarded")
            return None
        action, reason = find_bound_action(game_state, actions, expected)
        if action is None:
            self._clear_sticky_with_audit(game_state, "target_binding_invalid: " + reason)
            self.log_run_event(
                "RUN48_STICKY_TARGET_REPLAN", game_state,
                expected_action=expected, reason=reason,
                legal_actions=[x.get("description") for x in actions],
            )
            return None
        self._sticky_combat_remaining = remaining[1:]
        self.log_run_event(
            "STICKY_COMBAT_PLAN_FOLLOWED", game_state,
            expected_action=expected["description"],
            selected_action=action.get("description"),
            target_slot=expected.get("target_slot"),
            match_reason=reason,
            remaining_plan=self._sticky_combat_remaining,
            original_reason=getattr(self, "_sticky_combat_reason", None),
        )
        return action

    def choose_combat(self, game_state, actions):
        self._run48_current_actions = actions
        try:
            return super().choose_combat(game_state, actions)
        finally:
            self._run48_current_actions = None

    def add_memory_to_prompt(self, decision_type, prompt, game_state=None,
                             memory_category=None, output_instruction="Return ONLY the number."):
        augmented, category, ids = super().add_memory_to_prompt(
            decision_type, prompt, game_state=game_state,
            memory_category=memory_category, output_instruction=output_instruction,
        )
        if decision_type == "COMBAT_PLAN_VERIFIER_V13":
            monsters = (((game_state or {}).get("combat_state") or {}).get("monsters") or [])
            unknown = [m.get("name") for m in monsters if
                       not m.get("is_gone") and not m.get("half_dead") and
                       str(m.get("intent") or "").upper() in
                       {"DEBUG", "UNKNOWN", "NONE", ""}]
            if unknown:
                augmented += (
                    "\n\nRUN48 UNKNOWN-INTENT SAFETY: Live enemies with unknown "
                    "intent exist: " + ", ".join(str(x) for x in unknown) +
                    ". The displayed attack sum is only a KNOWN lower bound, "
                    "NOT zero total incoming damage. Never claim it is safe to "
                    "discard Block because unknown intents display zero. "
                    "Prefer plans justified by demonstrated executable cards "
                    "and preserved defense, not an unsupported lethal estimate."
                )
        return augmented, category, ids

    def _install_replacement_sticky_plan(self, game_state, actions, indexes, reason):
        original = list(getattr(self, "_run43_original_plan", None) or [])
        replacement = [actions[i].get("description") for i in indexes
                       if isinstance(i, int) and 0 <= i < len(actions)]
        accepted, detail = validate_action_sequence(game_state, actions, indexes)
        if not accepted:
            rejection = detail
        else:
            unsafe, detail = unknown_intent_defense_regression(
                game_state, original, replacement,
            )
            if unsafe:
                rejection = detail
            elif (original and run43.provable_simple_lethal(game_state, original)
                  and not run43.provable_simple_lethal(game_state, replacement)):
                rejection = "replacement discards provable basic-attack lethal"
            else:
                rejection = None
        if rejection:
            self.log_run_event(
                "RUN48_VERIFIER_REPLACEMENT_REJECTED", game_state,
                reason=rejection, original_plan=original,
                proposed_replacement=replacement, verifier_reason=reason,
            )
            raise ValueError("Run-48 verifier feasibility gate: " + rejection)

        # Bypass Run-43's blanket rejection of unknown intents, but use the
        # inherited verified-plan storage, then annotate target identities.
        selected, _ = super(run43.ContinualC2Run43Agent, self)._install_replacement_sticky_plan(
            game_state, actions, indexes, reason,
        )
        bound = bind_plan(game_state, actions, indexes)
        self._sticky_combat_remaining = bound[1:]
        self.log_run_event(
            "RUN48_VERIFIER_REPLACEMENT_ACCEPTED", game_state,
            original_plan=original, bound_actions=bound,
            verifier_reason=reason,
            unknown_intent_policy="reject_verified_block_loss_only",
        )
        return selected, bound


# Keep the legacy Run-43 launcher importable while making the canonical entry
# point instantiate v1.6 for Run 48 onward.
base.STSAgent = ContinualC2Run48Agent


def main():
    run43.main()


if __name__ == "__main__":
    main()
