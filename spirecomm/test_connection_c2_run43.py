"""Run-43 A10 controller: scoped human supersession + conservative verifier guards.

Import the frozen A10 wrapper and preserve all historical source and feedback.
Local Run-42 finalization AND an offline Run-42 checkpoint are prerequisites.
"""
from __future__ import annotations

import json
from pathlib import Path

import test_connection_c2_a10 as a10
from run43_policy import (
    OLD_RELIC_LESSON, NEW_RELIC_LESSON, SUPERSESSION_SCOPE,
    assert_relic_teaching_present, active_neow_rules, is_starting_relic_swap,
    neow_eligible_actions, validate_replacement_sequence,
    has_unknown_attack_intent, provable_simple_lethal,
)

base = a10.base
INTERVENTION_START_RUN = 43
VARIANT = "c2-v1.5.0-run43-active-supersession-verifier-guards+a10"
CHECKPOINT_FILE = (
    Path(__file__).resolve().parent / "runs" / "_local_checkpoints" /
    "C2_through_run42_pre_v1_5.zip"
)


def verify_run42_cutover(events_file, playbook_file, checkpoint_file):
    if not Path(checkpoint_file).is_file():
        raise ValueError(
            "Missing Run-42 offline checkpoint. With the game closed run "
            "python spirecomm/freeze_c2_run42_checkpoint.py first."
        )
    events = Path(events_file)
    if not events.is_file():
        raise ValueError("Run events ledger is missing.")
    finalized = False
    for line in events.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if (row.get("event_type") == "POST_RUN_REFLECTION_COMPLETE"
                and int(row.get("completed_run_number") or 0) == 42):
            finalized = True
            break
    if not finalized:
        raise ValueError("Run 42 must be fully reflected before Run 43.")
    with Path(playbook_file).open(encoding="utf-8") as stream:
        playbook = json.load(stream)
    if int(playbook.get("updated_through_run") or 0) < 42:
        raise ValueError("The active playbook has not incorporated Run 42.")
    assert_relic_teaching_present(playbook)
    return playbook


class ContinualC2Run43Agent(a10.ContinualC2A10Agent):
    def __init__(self, *args, **kwargs):
        # Validate before parent initialization can create any new run state.
        verify_run42_cutover(base.EVENTS_FILE, base.PLAYBOOK_FILE, CHECKPOINT_FILE)
        self._run43_neow_scope = False
        self._run43_original_plan = None
        super().__init__(*args, **kwargs)
        if self.completed_run_count < 42:
            raise ValueError("Run-43 intervention requires 42 completed runs.")
        assert_relic_teaching_present(self.playbook)

    def log_run_event(self, event_type, game_state=None, **details):
        details["controller_variant"] = VARIANT
        details.setdefault("run43_intervention_start_run", INTERVENTION_START_RUN)
        details.setdefault("human_policy_supersession", "run23-over-run1-neow-v1")
        return super().log_run_event(event_type, game_state, **details)

    def retrieve_memories(self, category):
        rules = super().retrieve_memories(category)
        if getattr(self, "_run43_neow_scope", False) and str(category).upper() == "GENERAL":
            return active_neow_rules(rules)
        return rules

    def choose_event(self, game_state, actions, label="EVENT_DECISION", memory_category="EVENT"):
        if label != SUPERSESSION_SCOPE:
            return super().choose_event(game_state, actions, label=label, memory_category=memory_category)

        assert_relic_teaching_present(self.playbook)
        allowed = neow_eligible_actions(actions)
        blocked = [a.get("description") for a in actions if a not in allowed]
        if blocked:
            self.log_run_event(
                "RUN43_HUMAN_SUPERSESSION_APPLIED", game_state,
                decision_type=label, superseded_memory_id=OLD_RELIC_LESSON,
                current_memory_id=NEW_RELIC_LESSON,
                suppressed_options=blocked,
                available_options=[a.get("description") for a in allowed],
            )
        self._run43_neow_scope = True
        try:
            selected = super().choose_event(game_state, allowed, label=label,
                                            memory_category=memory_category)
        finally:
            self._run43_neow_scope = False
        return selected

    def _verify_new_combat_plan(self, game_state, actions, selected):
        self._run43_original_plan = [selected.get("description")] + [
            row.get("description")
            for row in (getattr(self, "_sticky_combat_remaining", []) or [])
        ]
        try:
            return super()._verify_new_combat_plan(game_state, actions, selected)
        finally:
            self._run43_original_plan = None

    def _install_replacement_sticky_plan(self, game_state, actions, indexes, reason):
        original = list(getattr(self, "_run43_original_plan", None) or [])
        replacement = [actions[idx].get("description") for idx in indexes]
        accepted, detail = validate_replacement_sequence(game_state, actions, indexes)
        if not accepted:
            rejection = detail
        elif has_unknown_attack_intent(game_state):
            rejection = "unknown enemy intent: cannot assume zero incoming attack"
        elif original and provable_simple_lethal(game_state, original) and not provable_simple_lethal(game_state, replacement):
            rejection = "verifier would replace a provable basic-attack lethal sequence"
        else:
            rejection = None
        if rejection:
            self.log_run_event(
                "RUN43_VERIFIER_REPLACEMENT_REJECTED", game_state,
                reason=rejection, original_plan=original,
                rejected_replacement=replacement, verifier_reason=reason,
            )
            # The inherited verifier catches ValueError and retains the
            # original first-pass plan. No partial sticky-plan mutation.
            raise ValueError("Run-43 verifier safety gate: " + rejection)
        return super()._install_replacement_sticky_plan(
            game_state, actions, indexes, reason,
        )


# All historic imports remain in place. CommunicationMod constructs this
# subclass through the inherited entry point.
base.STSAgent = ContinualC2Run43Agent


def main():
    a10.main()


if __name__ == "__main__":
    main()
