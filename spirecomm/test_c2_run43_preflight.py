"""Pure synthetic checks for the Run-43 intervention (no game or LLM)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import run43_policy as policy
import test_connection_c2_run43 as run43

ARCHIVE = ROOT / "runs" / "C2_through_run38_pre_A10" / "condition_c2_playbook.json"


def fixture():
    with ARCHIVE.open(encoding="utf-8") as stream:
        return json.load(stream)


def state(hand, energy, hp=25, intent="ATTACK", enemy_hp=25, strength=2):
    return {
        "combat_state": {
            "player": {"energy": energy, "current_hp": hp,
                       "powers": [{"id": "Strength", "amount": strength}]},
            "hand": hand,
            "monsters": [{"name": "Gremlin Nob", "current_hp": enemy_hp,
                           "block": 0, "is_gone": False, "intent": intent,
                           "powers": [{"id": "Angry", "amount": 3}]}],
        }
    }


class Run43Preflight(unittest.TestCase):
    def test_historical_run1_and_corrective_run23_exist(self):
        playbook = fixture()
        policy.assert_relic_teaching_present(playbook)

    def test_neow_supersession_does_not_delete_historical_memory(self):
        obj = object.__new__(run43.ContinualC2Run43Agent)
        obj.playbook = fixture()
        obj._run43_neow_scope = True
        current = obj.retrieve_memories("GENERAL")
        sources = {v for row in current for v in row.get("source_memory_ids", [])}
        self.assertNotIn(policy.OLD_RELIC_LESSON, sources)
        self.assertIn(policy.NEW_RELIC_LESSON, sources)
        obj._run43_neow_scope = False
        historical = obj.retrieve_memories("GENERAL")
        sources = {v for row in historical for v in row.get("source_memory_ids", [])}
        self.assertIn(policy.OLD_RELIC_LESSON, sources)

    def test_guard_preserves_other_neow_options_and_logs_supersession(self):
        obj = object.__new__(run43.ContinualC2Run43Agent)
        obj.playbook = fixture()
        obj._run43_neow_scope = False
        events = []
        obj.log_run_event = lambda event, state, **kwargs: events.append((event, kwargs))
        swap = {"description": "[ Lose your starting Relic Obtain a random boss Relic ]", "command": "CHOOSE 3"}
        safe = {"description": "[ Max HP +8 ]", "command": "CHOOSE 1"}
        with patch.object(run43.a10.ContinualC2A10Agent, "choose_event",
                          side_effect=lambda gs, opts, **kw: opts[0]):
            result = obj.choose_event({}, [swap, safe],
                                      label="NEOW_BLESSING", memory_category="GENERAL")
        self.assertIs(result, safe)
        self.assertFalse(obj._run43_neow_scope)
        self.assertEqual(events[0][0], "RUN43_HUMAN_SUPERSESSION_APPLIED")

    def test_only_available_swap_keeps_game_legality(self):
        swap = {"description": "Lose your starting Relic Obtain a random boss Relic"}
        self.assertEqual(policy.neow_eligible_actions([swap]), [swap])

    def test_energy_invalid_four_cost_rejected(self):
        game = state([
            {"name": "Bash", "cost": 2},
            {"name": "Strike", "cost": 1},
            {"name": "Pommel Strike", "cost": 1},
        ], energy=3)
        actions = [{"description": x} for x in [
            "Play Bash on Gremlin Nob (25 HP)",
            "Play Strike on Gremlin Nob (25 HP)",
            "Play Pommel Strike on Gremlin Nob (25 HP)",
        ]]
        self.assertFalse(policy.validate_replacement_sequence(game, actions, [0,1,2])[0])
        self.assertTrue(policy.validate_replacement_sequence(game, actions, [0,1])[0])

    def test_duplicate_card_overuse_rejected(self):
        game = state([{"name": "Strike", "cost": 1}], energy=3)
        actions = [{"description": "Play Strike on Gremlin Nob (25 HP)"}]
        self.assertFalse(policy.validate_replacement_sequence(game, actions, [0,0])[0])

    def test_unknown_intent_is_not_non_attacking(self):
        game = state([], energy=3, intent="DEBUG")
        self.assertTrue(policy.has_unknown_attack_intent(game))
        game["combat_state"]["monsters"][0]["intent"] = "BUFF"
        self.assertFalse(policy.has_unknown_attack_intent(game))

    def test_simple_provable_nob_lethal(self):
        game = state([
            {"name": "Thunderclap", "cost": 1},
            {"name": "Strike", "cost": 1},
            {"name": "Strike", "cost": 1},
        ], energy=3, enemy_hp=25)
        seq = ["Play Thunderclap", "Play Strike on Gremlin Nob",
               "Play Strike on Gremlin Nob"]
        self.assertTrue(policy.provable_simple_lethal(game, seq))
        self.assertFalse(policy.provable_simple_lethal(game, seq[:2]))
        game["combat_state"]["player"]["powers"].append({"id": "Weak", "amount": 1})
        self.assertFalse(policy.provable_simple_lethal(game, seq))

    def test_verifier_rejects_unknown_intent_replacement(self):
        obj = object.__new__(run43.ContinualC2Run43Agent)
        obj._run43_original_plan = ["Play Defend"]
        events = []
        obj.log_run_event = lambda event, gs, **kw: events.append(event)
        game = state([{"name": "Strike", "cost": 1}], energy=3, intent="DEBUG")
        with self.assertRaisesRegex(ValueError, "unknown enemy intent"):
            obj._install_replacement_sticky_plan(
                game, [{"description": "Play Strike on Gremlin Nob"}], [0], "test")
        self.assertIn("RUN43_VERIFIER_REPLACEMENT_REJECTED", events)

    def test_verifier_rejects_losing_provable_lethal(self):
        obj = object.__new__(run43.ContinualC2Run43Agent)
        obj._run43_original_plan = ["Play Thunderclap",
                                     "Play Strike on Gremlin Nob",
                                     "Play Strike on Gremlin Nob"]
        obj.log_run_event = lambda *args, **kwargs: None
        game = state([{"name": "Thunderclap", "cost": 1},
                      {"name": "Strike", "cost": 1},
                      {"name": "Strike", "cost": 1},
                      {"name": "Defend", "cost": 1}], energy=3)
        actions = [{"description": "Play Defend"}]
        with self.assertRaisesRegex(ValueError, "provable basic-attack lethal"):
            obj._install_replacement_sticky_plan(game, actions, [0], "test")

    def test_active_entrypoint(self):
        self.assertIs(run43.base.STSAgent, run43.ContinualC2Run43Agent)
        self.assertTrue(issubclass(run43.ContinualC2Run43Agent,
                                   run43.a10.ContinualC2A10Agent))


if __name__ == "__main__":
    unittest.main(verbosity=2)
