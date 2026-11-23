"""Run-56 v1.7.1 offline tests (no game or API calls)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import run56_policy as policy
import test_connection_c2_run56 as v171


def lagavulin_state(hp=10, strength=-4, enemy_hp=22, relics=None):
    return {
        "current_hp": hp, "max_hp": 80, "room_phase": "COMBAT",
        "relics": [{"name": name} for name in
                   (["Burning Blood", "Toy Ornithopter"] if relics is None else relics)],
        "combat_state": {
            "turn": 8,
            "player": {
                "current_hp": hp, "max_hp": 80, "energy": 3,
                "block": 0, "powers": [{"id": "Strength", "amount": strength}],
            },
            "hand": [
                {"name": "Bash+", "cost": 2}, {"name": "Strike", "cost": 1},
                {"name": "Defend", "cost": 1},
            ],
            "monsters": [{
                "name": "Lagavulin", "current_hp": enemy_hp, "max_hp": 112,
                "is_gone": False, "intent": "ATTACK",
                "move_adjusted_damage": 20, "move_hits": 1,
            }],
        },
    }


def rule(number, category, guidance, source_run=54, authoritative=True):
    return {
        "rule_id": "rule_" + str(number), "category": category,
        "when": "When relevant", "guidance": guidance,
        "authoritative": authoritative,
        "source_memory_ids": ["c2_run_%02d_01" % source_run],
    }


class LethalScreen(unittest.TestCase):
    def test_run55_bash_strike_false_lethal(self):
        screen = policy.optimistic_attack_ceiling(
            lagavulin_state(),
            ["Play Bash+ on Lagavulin (22 HP)",
             "Play Strike on Lagavulin (22 HP)", "End turn"])
        self.assertEqual(screen["player_strength"], -4)
        self.assertEqual(screen["optimistic_damage_ceiling"], 16)
        self.assertTrue(screen["claimed_lethal_disproved"])

    def test_no_false_rejection_when_damage_could_kill(self):
        screen = policy.optimistic_attack_ceiling(
            lagavulin_state(enemy_hp=10),
            ["Play Bash+ on Lagavulin (10 HP)",
             "Play Strike on Lagavulin (10 HP)"])
        self.assertFalse(screen["claimed_lethal_disproved"])

    def test_abstains_for_unknown_attacks_relics_or_no_debuff(self):
        state = lagavulin_state()
        self.assertIsNone(policy.optimistic_attack_ceiling(
            state, ["Play Heavy Blade on Lagavulin (22 HP)"]))
        self.assertIsNone(policy.optimistic_attack_ceiling(
            lagavulin_state(relics=["Pen Nib"]),
            ["Play Bash+ on Lagavulin (22 HP)"]))
        self.assertIsNone(policy.optimistic_attack_ceiling(
            lagavulin_state(strength=0),
            ["Play Bash+ on Lagavulin (22 HP)"]))


class Retrieval(unittest.TestCase):
    def test_reward_category_lessons_not_crowded_out(self):
        state = lagavulin_state()
        state["choice_list"] = ["Take Panacea", "Take Trip", "Take Forethought"]
        extras = [rule(i, "COMBAT", "Burning Blood Trip Lagavulin survival", i)
                  for i in range(1, 14)]
        rewards = [rule(100 + i, "CARD_REWARD",
                        "For Panacea, Trip and Forethought evaluate reward synergy", 30+i)
                   for i in range(4)]
        selected, audit = policy.select_rules_v171(extras+rewards, "CARD_REWARD", state)
        self.assertGreaterEqual(sum(r["category"] == "CARD_REWARD"
                                    for r in selected), 2)
        self.assertEqual(audit["selected_count"], len(selected))
        self.assertEqual(audit["candidate_count"], len(extras+rewards))
        self.assertEqual(len({r["rule_id"] for r in selected}), len(selected))

    def test_critical_unknown_intent_pin_survives(self):
        state = lagavulin_state()
        state["combat_state"]["monsters"][0]["intent"] = "UNKNOWN"
        critical = rule(99, "GENERAL",
                        "UNKNOWN intent missing incoming damage is not zero")
        rules = [rule(i, "COMBAT", "Take sensible actions", i)
                 for i in range(20)] + [critical]
        selected, audit = policy.select_rules_v171(rules, "COMBAT", state)
        self.assertIn(critical["rule_id"], [r["rule_id"] for r in selected])
        self.assertIn(critical["rule_id"], audit["pinned_authoritative_ids"])

    def test_does_not_mutate_input(self):
        items = [rule(i, "CARD_REWARD", "Consider Trip", i) for i in range(15)]
        before = json.dumps(items, sort_keys=True)
        policy.select_rules_v171(items, "CARD_REWARD", {"choice_list": ["Trip"]})
        self.assertEqual(json.dumps(items, sort_keys=True), before)


class Cutover(unittest.TestCase):
    def make_files(self, root, status="FINALIZED"):
        review = root / "review.json"
        playbook = root / "playbook.json"
        events = root / "events.jsonl"
        checkpoint = root / "checkpoint.zip"
        packet = {"source_run": 55, "source_run_id": "run-55-test",
                  "status": status, "review_decision": "HUMAN_TEACHING",
                  "human_feedback": "Check actual Strength before claiming lethal"}
        review.write_text(json.dumps(packet))
        playbook.write_text('{"updated_through_run":55}')
        events.write_text(
            json.dumps({"event_type": "RUN_END", "completed_run_number": 55,
                        "run_id": "run-55-test"}) + "\n" +
            json.dumps({"event_type": "POST_RUN_REFLECTION_COMPLETE",
                        "completed_run_number": 55,
                        "reflected_run_id": "run-55-test"}) + "\n")
        with ZipFile(checkpoint, "w") as archive:
            archive.writestr("CHECKPOINT_MANIFEST.json",
                             json.dumps({"run": 55,
                                         "validation": {"source_run_id": "run-55-test"}}))
            archive.writestr(
                "reflection/condition_c2_outputs/run_55_feedback_review.json",
                json.dumps(packet))
        return events, playbook, review, checkpoint

    def test_requires_finalized_frozen_matching_run(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = self.make_files(root)
            self.assertEqual(v171.verify_run55_cutover(*args)
                             ["updated_through_run"], 55)
            args[3].unlink()
            with self.assertRaisesRegex(ValueError, "checkpoint missing"):
                v171.verify_run55_cutover(*args)
            args = self.make_files(root, status="PENDING")
            with self.assertRaisesRegex(ValueError, "FINALIZED"):
                v171.verify_run55_cutover(*args)


class Binding(unittest.TestCase):
    def test_new_launcher_binds_run56(self):
        import test_connection
        self.assertIs(v171.base.STSAgent, v171.ContinualC2Run56Agent)
        self.assertIs(test_connection.main, v171.main)

    def test_strength_warning_enters_verifier_prompt(self):
        agent = object.__new__(v171.ContinualC2Run56Agent)
        agent._run43_original_plan = [
            "Play Bash+ on Lagavulin (22 HP)",
            "Play Strike on Lagavulin (22 HP)"]
        agent.playbook = {"updated_through_run": 55}
        agent.retrieve_memories = lambda category: []
        agent.log_run_event = lambda *a, **kw: None
        result, _, _ = agent.add_memory_to_prompt(
            "COMBAT_PLAN_VERIFIER_V13", "Verifier", lagavulin_state(),
            "COMBAT")
        self.assertIn("Player Strength is -4", result)
        self.assertIn("RUN56 NONLETHAL CERTIFICATE", result)

    def test_known_survival_option_overrides_false_lethal(self):
        game = lagavulin_state(hp=18)
        selected = {"description": "Play Bash+ on Lagavulin (22 HP)", "command": "PLAY 1 0"}
        defend = {"description": "Play Defend", "command": "PLAY 3"}
        options = [selected, defend]
        agent = object.__new__(v171.ContinualC2Run56Agent)
        agent._sticky_combat_remaining = [
            {"description": "Play Strike on Lagavulin (22 HP)"}]
        events = []
        agent._clear_sticky_with_audit = lambda *a: agent._sticky_combat_remaining.clear()

        def fake_verifier(self, state, actions, first):
            self.log_run_event("COMBAT_PLAN_VERIFICATION_V13", state,
                               structured_payload={"approved": True,
                                                   "estimated_hp_loss": 0},
                               displayed_incoming_damage=20)
            return first

        with patch.object(v171.v17.ContinualC2Run55Agent,
                          "_verify_new_combat_plan", fake_verifier), \
             patch.object(v171.v17.ContinualC2Run55Agent,
                          "log_run_event",
                          lambda self, name, state=None, **kw: events.append(name)):
            chosen = agent._verify_new_combat_plan(game, options, selected)
        self.assertIs(chosen, defend)
        self.assertIn("RUN56_UNFOUNDED_LETHAL_FLAGGED", events)
        self.assertIn("RUN56_SURVIVAL_OVERRIDE", events)

    def test_no_override_when_defend_cannot_save(self):
        game = lagavulin_state(hp=10)
        selected = {"description": "Play Bash+ on Lagavulin (22 HP)", "command": "PLAY 1 0"}
        defend = {"description": "Play Defend", "command": "PLAY 3"}
        agent = object.__new__(v171.ContinualC2Run56Agent)
        agent._sticky_combat_remaining = [
            {"description": "Play Strike on Lagavulin (22 HP)"}]
        seen = []

        def fake_verifier(self, state, actions, first):
            self.log_run_event("COMBAT_PLAN_VERIFICATION_V13", state,
                               structured_payload={"approved": True,
                                                   "estimated_hp_loss": 0},
                               displayed_incoming_damage=20)
            return first

        with patch.object(v171.v17.ContinualC2Run55Agent,
                          "_verify_new_combat_plan", fake_verifier), \
             patch.object(v171.v17.ContinualC2Run55Agent,
                          "log_run_event",
                          lambda self, name, state=None, **kw: seen.append(name)):
            chosen = agent._verify_new_combat_plan(game, [selected, defend], selected)
        self.assertIs(chosen, selected)
        self.assertIn("RUN56_UNFOUNDED_LETHAL_FLAGGED", seen)
        self.assertNotIn("RUN56_SURVIVAL_OVERRIDE", seen)


if __name__ == "__main__":
    unittest.main(verbosity=2)
