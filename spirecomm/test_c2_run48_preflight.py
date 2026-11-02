"""Run 48 offline regression tests; no game or LLM calls."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run48_policy as policy
import test_connection_c2_run48 as v16


def state(energy=3, names=("Bash+", "Pommel Strike", "Strike"), intent="ATTACK"):
    return {"act": 1, "floor": 8, "room_type": "EliteRoom",
            "room_phase": "COMBAT", "screen_type": "NONE",
            "combat_state": {
                "turn": 4, "player": {"current_hp": 31, "max_hp": 80,
                                        "energy": energy, "block": 0, "powers": []},
                "hand": [{"name": n, "cost": 2 if n.startswith("Bash") else 1,
                          "is_playable": True} for n in names],
                "monsters": [
                    {"name": "Sentry", "current_hp": 19, "max_hp": 42, "block": 0,
                     "intent": intent, "is_gone": False},
                    {"name": "Sentry", "current_hp": 22, "max_hp": 44, "block": 0,
                     "intent": "ATTACK", "is_gone": False},
                    {"name": "Sentry", "current_hp": 31, "max_hp": 44, "block": 0,
                     "intent": "DEBUFF", "is_gone": False}]}}


def action(name, card_index, target=0, hp=19):
    return {"command": f"PLAY {card_index} {target}",
            "description": f"Play {name} on Sentry ({hp} HP)", "kind": "card"}


class V16Tests(unittest.TestCase):
    def test_same_name_sentry_target_preserved_after_hp_change(self):
        game = state()
        expected = policy.bind_plan(game, [action("Pommel Strike", 2, 0)], [0])[0]
        game["combat_state"]["monsters"][0]["current_hp"] = 9
        selected, _ = policy.find_bound_action(
            game, [action("Pommel Strike", 2, 1, 22),
                   action("Pommel Strike", 2, 0, 9)], expected)
        self.assertEqual(selected["command"], "PLAY 2 0")

    def test_same_name_same_max_hp_slot_preserved(self):
        game = state()
        game["combat_state"]["monsters"][0]["max_hp"] = 44
        bound = policy.bind_plan(game, [action("Strike", 3, 1, 22)], [0])[0]
        selected, _ = policy.find_bound_action(
            game, [action("Strike", 3, 0), action("Strike", 3, 1, 22)], bound)
        self.assertEqual(selected["command"], "PLAY 3 1")

    def test_roster_change_invalidates_target(self):
        game = state()
        bound = policy.bind_plan(game, [action("Pommel Strike", 2, 0)], [0])[0]
        game["combat_state"]["monsters"].pop(0)
        found, reason = policy.find_bound_action(
            game, [action("Pommel Strike", 2, 0, 22)], bound)
        self.assertIsNone(found)
        self.assertIn("roster changed", reason)

    def test_actual_sticky_execution_keeps_target(self):
        game = state()
        bound = policy.bind_plan(game, [action("Pommel Strike", 2, 0)], [0])[0]
        agent = object.__new__(v16.ContinualC2Run48Agent)
        agent.current_run_id = "run46-test"
        agent._sticky_combat_turn = 4
        agent._sticky_combat_run_id = "run46-test"
        agent._sticky_combat_remaining = [bound]
        agent._sticky_combat_reason = "finish attacker"
        agent.log_run_event = lambda *args, **kwargs: None
        game["combat_state"]["monsters"][0]["current_hp"] = 9
        chosen = agent._try_follow_sticky_plan(
            game, [action("Pommel Strike", 2, 1, 22),
                   action("Pommel Strike", 2, 0, 9)])
        self.assertEqual(chosen["command"], "PLAY 2 0")
        self.assertEqual(agent._sticky_combat_remaining, [])

    def test_repeated_same_hand_card_rejected_even_with_different_targets(self):
        game = state()
        options = [action("Pommel Strike", 2, 0),
                   action("Pommel Strike", 2, 1, 22)]
        valid, reason = policy.validate_action_sequence(game, options, [0, 1])
        self.assertFalse(valid)
        self.assertIn("same physical", reason)

    def test_run46_three_strikes_with_only_two_rejected(self):
        game = state(names=("Strike", "Strike", "Defend"))
        opts = [action("Strike", 1), action("Strike", 2)]
        valid, reason = policy.validate_action_sequence(game, opts, [0, 1, 0])
        self.assertFalse(valid)
        self.assertIn("same physical", reason)

    def test_run41_four_energy_plan_rejected(self):
        game = state(energy=3)
        opts = [action("Bash+", 1), action("Pommel Strike", 2),
                action("Strike", 3)]
        valid, reason = policy.validate_action_sequence(game, opts, [0, 1, 2])
        self.assertFalse(valid)
        self.assertIn("energy", reason)

    def test_valid_bash_pommel_allowed(self):
        game = state()
        opts = [action("Bash+", 1), action("Pommel Strike", 2)]
        self.assertTrue(policy.validate_action_sequence(game, opts, [0, 1])[0])

    def test_unknown_intent_offensive_replacement_allowed(self):
        game = state(intent="UNKNOWN")
        self.assertFalse(policy.unknown_intent_defense_regression(
            game, ["Play Strike on Sentry"], ["Play Pommel Strike on Sentry"])[0])

    def test_unknown_intent_losing_block_rejected(self):
        game = state(intent="UNKNOWN")
        unsafe, reason = policy.unknown_intent_defense_regression(
            game, ["Play Defend"], ["Play Strike on Sentry"])
        self.assertTrue(unsafe)
        self.assertIn("Block", reason)

    def test_known_intent_not_blanket_blocked(self):
        game = state(intent="ATTACK")
        self.assertFalse(policy.unknown_intent_defense_regression(
            game, ["Play Defend"], ["Play Strike on Sentry"])[0])

    def test_run47_checkpoint_precondition(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            event = p / "events.jsonl"
            book = p / "playbook.json"
            review = p / "review.json"
            checkpoint = p / "checkpoint.zip"
            event.write_text(json.dumps({"event_type": "POST_RUN_REFLECTION_COMPLETE",
                                         "completed_run_number": 47}) + "\n")
            book.write_text('{"updated_through_run":47}')
            review.write_text('{"status":"FINALIZED","source_run":47}')
            checkpoint.write_bytes(b"test")
            self.assertEqual(v16.verify_run47_cutover(
                event, book, review, checkpoint)["updated_through_run"], 47)
            review.write_text('{"status":"PENDING","source_run":47}')
            with self.assertRaisesRegex(ValueError, "FINALIZED"):
                v16.verify_run47_cutover(event, book, review, checkpoint)

    def test_unknown_replacement_bypasses_old_blanket_gate(self):
        game = state(intent="UNKNOWN")
        opts = [action("Pommel Strike", 2)]
        agent = object.__new__(v16.ContinualC2Run48Agent)
        agent._run43_original_plan = ["Play Strike on Sentry"]
        agent.current_run_id = "synthetic"
        agent.log_run_event = lambda *args, **kwargs: None
        def inherited(self, gs, actions, indexes, reason):
            return actions[indexes[0]], []
        with patch.object(v16.run43.a10.ContinualC2A10Agent,
                          "_install_replacement_sticky_plan", inherited,
                          create=True):
            chosen, planned = agent._install_replacement_sticky_plan(
                game, opts, [0], "prefer threatening enemy")
        self.assertEqual(chosen["command"], "PLAY 2 0")
        self.assertEqual(planned[0]["target_slot"], 0)

    def test_new_controller_owns_launcher_binding(self):
        self.assertIs(v16.base.STSAgent, v16.ContinualC2Run48Agent)


if __name__ == "__main__":
    unittest.main(verbosity=2)
