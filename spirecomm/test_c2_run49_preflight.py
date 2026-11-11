"""Run-49 v1.6.1 offline regression tests; no game, LLM or API calls."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run49_policy as policy
import test_connection_c2_run49 as v161


def state(names=("Strike", "Strike"), energy=3, relics=()):
    return {
        "act": 1, "floor": 13, "room_phase": "COMBAT",
        "relics": [{"name": name} for name in relics],
        "combat_state": {
            "turn": 4, "player": {"energy": energy, "block": 0, "powers": []},
            "hand": [{"name": name, "cost": 1, "cost_for_turn": 1,
                      "is_playable": True} for name in names],
            "monsters": [
                {"name": "Sentry", "id": "Sentry", "current_hp": 19,
                 "max_hp": 42, "is_gone": False, "intent": "ATTACK"},
                {"name": "Sentry", "id": "Sentry", "current_hp": 22,
                 "max_hp": 44, "is_gone": False, "intent": "ATTACK"},
            ],
        },
    }


def action(name, hand_slot, target=0, hp=19):
    if target is None:
        return {"description": f"Play {name}", "command": f"PLAY {hand_slot}",
                "kind": "card"}
    return {"description": f"Play {name} on Sentry ({hp} HP)",
            "command": f"PLAY {hand_slot} {target}", "kind": "card"}


class CardEquivalenceTests(unittest.TestCase):
    def test_run48_lagavulin_duplicate_strikes_after_first_card(self):
        game = state()
        game["combat_state"]["monsters"] = [{
            "name": "Lagavulin", "id": "Lagavulin", "max_hp": 112,
            "current_hp": 112, "is_gone": False, "intent": "SLEEP"}]
        first = {"description": "Play Strike on Lagavulin (112 HP)",
                 "command": "PLAY 1 0"}
        second = {"description": "Play Strike on Lagavulin (112 HP)",
                  "command": "PLAY 2 0"}
        bound = policy.bind_plan_v161(game, [first, second], [0, 1])[1]
        game["combat_state"]["hand"].pop(0)
        game["combat_state"]["monsters"][0]["current_hp"] = 106
        remaining = [{"description": "Play Strike on Lagavulin (106 HP)",
                      "command": "PLAY 1 0"}]
        selected, why, count = policy.find_equivalent_bound_action(
            game, remaining, bound)
        self.assertEqual(selected["command"], "PLAY 1 0")
        self.assertEqual(count, 1)

    def test_run48_same_target_multiple_strikes_choose_equivalent(self):
        game = state()
        planned = policy.bind_plan_v161(game, [action("Strike", 2)], [0])[0]
        options = [action("Strike", 2), action("Strike", 1)]
        picked, why, count = policy.find_equivalent_bound_action(
            game, options, planned)
        self.assertEqual(picked["command"], "PLAY 1 0")
        self.assertEqual(count, 2)
        self.assertIn("equivalent", why)

    def test_run48_duplicate_defend_can_continue(self):
        game = state(names=("Defend", "Defend", "Strike"))
        bound = policy.bind_plan_v161(
            game, [action("Defend", 2, target=None)], [0])[0]
        picked, why, count = policy.find_equivalent_bound_action(
            game, [action("Defend", 2, target=None),
                   action("Defend", 1, target=None)], bound)
        self.assertEqual(picked["command"], "PLAY 1")
        self.assertEqual(count, 2)

    def test_run48_duplicate_pommel_same_target(self):
        game = state(names=("Pommel Strike", "Pommel Strike"))
        planned = policy.bind_plan_v161(
            game, [action("Pommel Strike", 2, 1, 22)], [0])[0]
        options = [action("Pommel Strike", 1, 0, 19),
                   action("Pommel Strike", 1, 1, 22),
                   action("Pommel Strike", 2, 1, 22)]
        picked, _, count = policy.find_equivalent_bound_action(
            game, options, planned)
        self.assertEqual(picked["command"], "PLAY 1 1")
        self.assertEqual(count, 2)

    def test_run46_wrong_same_name_enemy_never_selected(self):
        game = state(names=("Bash+", "Pommel Strike"))
        planned = policy.bind_plan_v161(
            game, [action("Pommel Strike", 2, 0, 19)], [0])[0]
        game["combat_state"]["monsters"][0]["current_hp"] = 9
        picked, _, _ = policy.find_equivalent_bound_action(
            game, [action("Pommel Strike", 2, 1, 22),
                   action("Pommel Strike", 2, 0, 9)], planned)
        self.assertEqual(picked["command"], "PLAY 2 0")

    def test_missing_original_target_does_not_retarget(self):
        game = state()
        bound = policy.bind_plan_v161(game, [action("Strike", 2, 0)], [0])[0]
        game["combat_state"]["monsters"][0]["is_gone"] = True
        picked, why, _ = policy.find_equivalent_bound_action(
            game, [action("Strike", 2, 1, 22)], bound)
        self.assertIsNone(picked)
        self.assertIn("defeated", why)

    def test_monster_roster_shift_forces_replan(self):
        game = state()
        bound = policy.bind_plan_v161(game, [action("Strike", 2, 1, 22)], [0])[0]
        game["combat_state"]["monsters"].pop(0)
        picked, why, _ = policy.find_equivalent_bound_action(
            game, [action("Strike", 2, 0, 22)], bound)
        self.assertIsNone(picked)
        self.assertIn("roster changed", why)

    def test_cost_changed_no_longer_equivalent(self):
        game = state()
        bound = policy.bind_plan_v161(game, [action("Strike", 2)], [0])[0]
        game["combat_state"]["hand"][0]["cost_for_turn"] = 0
        game["combat_state"]["hand"][1]["cost_for_turn"] = 0
        picked, why, _ = policy.find_equivalent_bound_action(
            game, [action("Strike", 1), action("Strike", 2)], bound)
        self.assertIsNone(picked)
        self.assertIn("no longer available", why)

    def test_cost_changed_on_one_copy_choose_original_semantics_only(self):
        game = state()
        bound = policy.bind_plan_v161(game, [action("Strike", 2)], [0])[0]
        game["combat_state"]["hand"][0]["cost_for_turn"] = 0
        picked, _, _ = policy.find_equivalent_bound_action(
            game, [action("Strike", 1), action("Strike", 2)], bound)
        self.assertEqual(picked["command"], "PLAY 2 0")

    def test_original_uuid_preferred_when_both_copies_same(self):
        game = state()
        game["combat_state"]["hand"][0]["uuid"] = "first"
        game["combat_state"]["hand"][1]["uuid"] = "second"
        bound = policy.bind_plan_v161(game, [action("Strike", 2)], [0])[0]
        picked, why, count = policy.find_equivalent_bound_action(
            game, [action("Strike", 1), action("Strike", 2)], bound)
        self.assertEqual(picked["command"], "PLAY 2 0")
        self.assertIn("exact original", why)
        self.assertEqual(count, 2)

    def test_different_non_card_slot_does_not_get_guessed(self):
        game = state()
        selected, reason, count = policy.find_equivalent_bound_action(
            game, [{"description":"Use Strength Potion", "command":"POTION use 0"},
                   {"description":"Use Strength Potion", "command":"POTION use 1"}],
            {"description":"Use Strength Potion",
             "signature":"use strength potion"})
        self.assertIsNone(selected)
        self.assertEqual(count, 2)
        self.assertIn("non-card", reason)

    def test_run49_sticky_agent_logs_card_equivalence(self):
        game = state()
        bound = policy.bind_plan_v161(game, [action("Strike", 2)], [0])[0]
        agent = object.__new__(v161.ContinualC2Run49Agent)
        agent.current_run_id = "run49-synthetic"
        agent._sticky_combat_turn = 4
        agent._sticky_combat_run_id = "run49-synthetic"
        agent._sticky_combat_remaining = [bound]
        agent._sticky_combat_reason = "kill first Sentry"
        events = []
        agent.log_run_event = lambda event, gs, **kw: events.append((event, kw))
        selected = agent._try_follow_sticky_plan(
            game, [action("Strike", 2), action("Strike", 1)])
        self.assertEqual(selected["command"], "PLAY 1 0")
        self.assertEqual(agent._sticky_combat_remaining, [])
        self.assertIn("RUN49_EQUIVALENT_CARD_MATCH", [e for e, _ in events])

    def test_run49_sticky_changed_target_replans_not_wrong_target(self):
        game = state()
        bound = policy.bind_plan_v161(game, [action("Strike", 2)], [0])[0]
        game["combat_state"]["monsters"][0]["is_gone"] = True
        agent = object.__new__(v161.ContinualC2Run49Agent)
        agent.current_run_id = "run49-synthetic"
        agent._sticky_combat_turn = 4
        agent._sticky_combat_run_id = "run49-synthetic"
        agent._sticky_combat_remaining = [bound]
        agent._sticky_combat_reason = ""
        agent._clear_sticky_with_audit = lambda *args: setattr(
            agent, "_sticky_combat_remaining", [])
        events = []
        agent.log_run_event = lambda event, gs, **kw: events.append(event)
        self.assertIsNone(agent._try_follow_sticky_plan(
            game, [action("Strike", 2, 1, 22)]))
        self.assertIn("RUN49_STICKY_TARGET_REPLAN", events)


class ZeroEnergyWhirlwindTests(unittest.TestCase):
    @staticmethod
    def game(energy=0, relics=()):
        gs = state(names=("Whirlwind", "Strike"), energy=energy, relics=relics)
        gs["combat_state"]["hand"][0].update(
            cost=-1, cost_for_turn=-1)
        return gs

    @staticmethod
    def options():
        return [{"description": "Play Whirlwind", "command": "PLAY 1"},
                {"description": "End turn", "command": "END"}]

    def guard(self, gs, reason="Whirlwind deals 5 damage to each slime."):
        return policy.reject_unfounded_zero_energy_whirlwind(
            gs, self.options(), [0], ["End turn"], reason)

    def test_run48_zero_energy_fake_damage_rejected(self):
        bad, reason = self.guard(self.game())
        self.assertTrue(bad)
        self.assertIn("zero-energy Whirlwind", reason)

    def test_nonzero_energy_whirlwind_not_rejected(self):
        self.assertFalse(self.guard(self.game(energy=1))[0])

    def test_chemical_x_zero_energy_not_rejected(self):
        self.assertFalse(self.guard(self.game(relics=("Chemical X",)))[0])

    def test_kunai_trigger_only_if_zero_damage_acknowledged(self):
        game = self.game(relics=("Kunai",))
        self.assertFalse(self.guard(game,
            "0 damage at zero energy, but a third attack triggers Kunai.")[0])
        self.assertTrue(self.guard(game,
            "Kunai triggers and Whirlwind deals 5 damage at zero energy.")[0])

    def test_no_original_end_turn_not_rejected(self):
        self.assertFalse(policy.reject_unfounded_zero_energy_whirlwind(
            self.game(), self.options(), [0], ["Play Defend"], "Whirlwind")[0])

    def test_actual_verifier_method_rejects_and_logs(self):
        game = self.game(relics=("Kunai",))
        opts = self.options()
        agent = object.__new__(v161.ContinualC2Run49Agent)
        agent._run43_original_plan = ["End turn"]
        events = []
        agent.log_run_event = lambda n, gs, **kw: events.append(n)
        with self.assertRaisesRegex(ValueError, "Run-49 X-cost guard"):
            agent._install_replacement_sticky_plan(
                game, opts, [0], "Whirlwind deals 5 damage per slime.")
        self.assertIn("RUN49_X_COST_REPLACEMENT_REJECTED", events)

    def test_unknown_energy_not_speculatively_rejected(self):
        game = self.game()
        game["combat_state"]["player"]["energy"] = None
        self.assertFalse(self.guard(game)[0])


class Run49BoundaryTests(unittest.TestCase):
    def test_run48_finalized_playbook_checkpoint_and_complete_required(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            events = p / "events.jsonl"
            book = p / "playbook.json"
            review = p / "review.json"
            checkpoint = p / "checkpoint.zip"
            events.write_text(json.dumps({
                "event_type":"POST_RUN_REFLECTION_COMPLETE",
                "completed_run_number":48,
            }) + "\n")
            book.write_text('{"updated_through_run":48}')
            review.write_text(
                '{"source_run":48,"status":"FINALIZED","review_decision":"HUMAN_TEACHING"}')
            checkpoint.write_bytes(b"synthetic")
            self.assertEqual(v161.verify_run48_cutover(
                events, book, review, checkpoint)["updated_through_run"], 48)
            review.write_text('{"source_run":48,"status":"PENDING"}')
            with self.assertRaisesRegex(ValueError, "not FINALIZED"):
                v161.verify_run48_cutover(events, book, review, checkpoint)
            review.write_text(
                '{"source_run":48,"status":"FINALIZED","review_decision":"HUMAN_TEACHING"}')
            events.write_text("")
            with self.assertRaisesRegex(ValueError, "POST_RUN"):
                v161.verify_run48_cutover(events, book, review, checkpoint)

    def test_run49_provenance_label_for_new_events(self):
        agent = object.__new__(v161.ContinualC2Run49Agent)
        agent._run48_current_actions = None
        captured = []
        with patch.object(
            v161.run48.run43.a10.ContinualC2A10Agent,
            "log_run_event",
            lambda self, typ, gs=None, **kwargs: captured.append((typ, kwargs)),
        ):
            agent.log_run_event("RUN_START", None, active_ascension=10)
        self.assertEqual(captured[0][1]["controller_variant"], v161.VARIANT)
        self.assertEqual(captured[0][1]["run49_intervention_start_run"], 49)

    def test_valid_first_pass_binds_card_effect(self):
        game = state(names=("Strike", "Strike"))
        opts = [action("Strike", 1), action("Strike", 2)]
        agent = object.__new__(v161.ContinualC2Run49Agent)
        agent._run48_current_actions = opts
        agent._sticky_combat_remaining = []
        captured = []
        with patch.object(
            v161.run48.run43.a10.ContinualC2A10Agent,
            "log_run_event",
            lambda self, typ, gs=None, **kw: captured.append((typ, kw)),
        ):
            agent.log_run_event(
                "STICKY_COMBAT_PLAN_CREATED", game,
                action_sequence=[0,1], selected_action="Play Strike")
        self.assertEqual(len(agent._sticky_combat_remaining), 1)
        self.assertIn("card_effect_profile", agent._sticky_combat_remaining[0])

    def test_run49_is_active_launcher_class(self):
        self.assertIs(v161.base.STSAgent, v161.ContinualC2Run49Agent)


if __name__ == "__main__":
    unittest.main(verbosity=2)
