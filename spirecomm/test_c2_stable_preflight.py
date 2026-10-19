from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
CONTROLLER = ROOT / "test_connection_c2_stable.py"

spec = importlib.util.spec_from_file_location("_c2_stable_test", CONTROLLER)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load stable C2 controller")
stable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stable)


def state(floor=1, intent="ATTACK", damage=8, frail=False, energy=3):
    powers = [{"id": "Frail", "amount": 1}] if frail else []
    return {
        "act": 1, "floor": floor, "room_type": "MonsterRoom",
        "screen_type": "NONE", "room_phase": "COMBAT",
        "combat_state": {
            "turn": 1,
            "player": {
                "current_hp": 12, "max_hp": 80,
                "energy": energy, "block": 0, "powers": powers,
            },
            "hand": [
                {"name": "Defend", "cost": 1, "is_playable": True},
                {"name": "Strike", "cost": 1, "is_playable": True},
            ],
            "monsters": [{
                "name": "Test Louse", "current_hp": 9,
                "max_hp": 9, "block": 0, "is_gone": False,
                "intent": intent, "move_adjusted_damage": damage,
                "move_hits": 1,
            }],
        },
    }


class StableControllerPreflight(unittest.TestCase):
    def setUp(self):
        # Pure unit fixture — no OpenAI or CommunicationMod calls.
        self.agent = object.__new__(stable.ContinualC2StableAgent)
        self.agent.use_llm = False
        self.agent.current_run_id = "synthetic-test-run"
        self.agent._stable_encounter_key = None
        self.agent._sticky_combat_turn = None
        self.agent._sticky_combat_run_id = None
        self.agent._sticky_combat_remaining = []
        self.agent._sticky_combat_reason = None
        self.events = []
        self.agent.log_run_event = (
            lambda event_type, game_state=None, **kw:
            self.events.append((event_type, kw))
        )
        self.agent.log_debug = lambda *args, **kw: None

    def test_version_and_policy(self):
        self.assertEqual(stable.INTERVENTION_START_RUN, 37)
        self.assertEqual(stable.MEMORY_POLICY,
                         "all_applicable_rules_no_topk_with_context_pinning_v1")
        self.assertIs(
            stable.v131.v130.v121.v120.v112.v111.v11.prior.base.STSAgent,
            stable.ContinualC2StableAgent,
        )

    def test_encounter_change_clears_stale_end_turn(self):
        old = state(floor=2)
        new = state(floor=3)
        self.agent._sync_encounter(old)
        self.agent._sticky_combat_turn = 1
        self.agent._sticky_combat_run_id = self.agent.current_run_id
        self.agent._sticky_combat_remaining = [{
            "description": "End turn", "signature": "end turn",
        }]
        self.agent._sync_encounter(new)
        self.assertEqual(self.agent._sticky_combat_remaining, [])
        self.assertTrue(any(
            name == "STABLE_STICKY_PLAN_INVALIDATED"
            for name, _ in self.events
        ))

    def test_noncombat_screen_clears_sticky(self):
        self.agent._sync_encounter(state(floor=2))
        self.agent._sticky_combat_remaining = [{
            "description": "Play Strike on Test Louse", "signature": "play strike on test louse"
        }]
        self.agent._sync_encounter({
            "screen_type": "COMBAT_REWARD", "room_phase": "COMPLETE",
            "act": 1, "floor": 2,
        })
        self.assertEqual(self.agent._sticky_combat_remaining, [])

    def test_unsafe_end_turn_forces_defense(self):
        s = state(damage=8)
        actions = [
            {"command": "PLAY 0", "description": "Play Defend", "kind": "play"},
            {"command": "END", "description": "End turn", "kind": "end"},
        ]
        self.agent._sync_encounter(s)
        result = self.agent.choose_combat(s, actions)
        self.assertEqual(result["description"], "Play Defend")
        self.assertTrue(any(
            name == "STABLE_END_TURN_GUARD"
            for name, _ in self.events
        ))

    def test_dont_waste_block_when_no_attack(self):
        s = state(intent="BUFF", damage=0)
        actions = [
            {"command": "PLAY 0", "description": "Play Defend", "kind": "play"},
            {"command": "END", "description": "End turn", "kind": "end"},
        ]
        self.agent._sync_encounter(s)
        result = self.agent.choose_combat(s, actions)
        self.assertEqual(result["description"], "End turn")
        self.assertFalse(any(
            name == "STABLE_END_TURN_GUARD"
            for name, _ in self.events
        ))

    def test_frail_block_is_reduced(self):
        s = state(damage=8, frail=True)
        actions = [
            {"command": "PLAY 0", "description": "Play Defend", "kind": "play"},
            {"command": "END", "description": "End turn", "kind": "end"},
        ]
        selection = self.agent._best_immediate_block_action(s, actions)
        self.assertEqual(selection["description"], "Play Defend")
        projection = stable.v131.project_simple_block(
            s["combat_state"]["player"], ["Play Defend"]
        )
        self.assertEqual(projection["known_added_block"], 3)

    def test_orichalcum_not_overridden_by_worse_defend(self):
        s = state(damage=8)
        s["relics"] = [{"name": "Orichalcum"}]
        actions = [
            {"command": "PLAY 0", "description": "Play Defend", "kind": "play"},
            {"command": "END", "description": "End turn", "kind": "end"},
        ]
        self.agent._sync_encounter(s)
        result = self.agent.choose_combat(s, actions)
        # Ending with 0 Block gives 6 free Orichalcum Block, which is
        # better than playing a Defend for 5 and disabling Orichalcum.
        self.assertEqual(result["description"], "End turn")

    def test_orichalcum_can_be_beaten_by_better_block(self):
        s = state(damage=12)
        s["relics"] = [{"name": "Orichalcum"}]
        s["combat_state"]["hand"][0]["name"] = "Ghostly Armor+"
        actions = [
            {"command": "PLAY 0", "description": "Play Ghostly Armor+", "kind": "play"},
            {"command": "END", "description": "End turn", "kind": "end"},
        ]
        self.agent._sync_encounter(s)
        result = self.agent.choose_combat(s, actions)
        self.assertEqual(result["description"], "Play Ghostly Armor+")

    def test_queued_end_turn_not_blindly_followed(self):
        s = state(floor=2)
        actions = [
            {"command": "PLAY 0", "description": "Play Defend", "kind": "play"},
            {"command": "END", "description": "End turn", "kind": "end"},
        ]
        self.agent._sync_encounter(s)
        self.agent._sticky_combat_turn = 1
        self.agent._sticky_combat_run_id = self.agent.current_run_id
        self.agent._sticky_combat_remaining = [{
            "description": "End turn", "signature": "end turn",
        }]
        selected = self.agent.choose_combat(s, actions)
        self.assertEqual(selected["description"], "Play Defend")
        self.assertEqual(self.agent._sticky_combat_remaining, [])
        self.assertTrue(any(
            name == "STABLE_STICKY_PLAN_INVALIDATED"
            for name, _ in self.events
        ))

    def test_live_cumulative_memory_coverage(self):
        raw_path = PROJECT / "reflection" / "condition_c2_raw_memory.jsonl"
        pb_path = PROJECT / "reflection" / "condition_c2_playbook.json"
        if not raw_path.exists() or not pb_path.exists():
            self.skipTest("Local continual experiment data are not present")
        raw = [
            json.loads(line)
            for line in raw_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        playbook = json.loads(pb_path.read_text(encoding="utf-8"))
        rules = [
            rule
            for rows in playbook.get("categories", {}).values()
            for rule in rows
        ]
        covered = {
            memory_id
            for rule in rules
            for memory_id in rule.get("source_memory_ids", [])
        }
        missing = sorted({item["id"] for item in raw} - covered)
        self.assertFalse(missing, f"Raw human lessons dropped: {missing}")
        self.assertGreaterEqual(playbook.get("updated_through_run", 0), 36)


if __name__ == "__main__":
    unittest.main(verbosity=2)
