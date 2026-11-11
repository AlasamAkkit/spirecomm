"""Run-48 C2-only controller-attribution reflection regression."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from followup_reflection import build_controller_attribution_appendix


class ControllerAttributionTests(unittest.TestCase):
    def test_previous_run_phases_unchanged(self):
        events = [
            {"event_type": "RUN_START", "controller_variant": "c2-v1.5.0-run43"},
            {"event_type": "COMBAT_PLAN_VERIFICATION_V13",
             "verifier_replaced_plan": True}
        ]
        self.assertEqual(build_controller_attribution_appendix(events), "")

    def test_run48_preserves_original_and_replacement_separately(self):
        events = [
            {"event_type": "RUN_START",
             "controller_variant": "c2-v1.6.0-run48-target-identity-plan-feasibility+a10"},
            {"event_type": "COMBAT_PLAN_VERIFICATION_V13",
             "act": 1, "floor": 8,
             "proposed_sequence_descriptions": ["Play Bash+ on Sentry (19 HP)",
                                                 "Play Pommel Strike on Sentry (19 HP)"],
             "verifier_replaced_plan": True,
             "final_planned_actions": [{"description": "Play Defend"}],
             "final_selected_action": "Play Defend"},
            {"event_type": "RUN48_STICKY_TARGET_REPLAN", "act": 1, "floor": 8,
             "expected_action": {"description": "Play Pommel Strike on Sentry (19 HP)"},
             "reason": "target slot no longer matches"},
        ]
        appendix = build_controller_attribution_appendix(events)
        self.assertIn("original_actor_plan", appendix)
        self.assertIn("Play Bash+ on Sentry", appendix)
        self.assertIn("replacement_plan", appendix)
        self.assertIn("RUN48_STICKY_TARGET_REPLAN", appendix)
        self.assertIn("must NOT", appendix)

    def test_run49_card_and_xcost_interventions_recorded(self):
        events = [
            {"event_type": "RUN_START", "controller_variant":
             "c2-v1.6.1-run49-equivalent-card-xcost-guard+a10"},
            {"event_type": "RUN49_EQUIVALENT_CARD_MATCH",
             "floor": 6, "candidate_count": 2, "selected_command": "PLAY 1 0"},
            {"event_type": "RUN49_X_COST_REPLACEMENT_REJECTED",
             "floor": 8, "original_plan": ["End turn"],
             "reason": "zero-energy Whirlwind cannot deal baseline damage"},
        ]
        appendix = build_controller_attribution_appendix(events)
        self.assertIn("RUN49_EQUIVALENT_CARD_MATCH", appendix)
        self.assertIn("RUN49_X_COST_REPLACEMENT_REJECTED", appendix)
        self.assertIn("PLAY 1 0", appendix)

    def test_run48_without_interventions_does_not_invent_mistakes(self):
        appendix = build_controller_attribution_appendix([{
            "event_type": "RUN_START",
            "controller_variant": "c2-v1.6.0-run48-target-identity-plan-feasibility+a10"}])
        self.assertIn("No logged verifier replacement", appendix)


if __name__ == "__main__":
    unittest.main()
