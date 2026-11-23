"""Offline Run-55 v1.7 regression tests; no gameplay or API calls."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import freeze_c2_run54_checkpoint as freeze
import run55_policy as policy
import test_connection_c2_run55 as v17


def _rule(rule_id, text, *, authoritative=True, run=10):
    return {
        "rule_id": rule_id,
        "guidance": text,
        "when": "When context is relevant",
        "category": "COMBAT",
        "authoritative": authoritative,
        "source_memory_ids": [f"c2_run_{run:02d}_01"],
    }


class JsonRepair(unittest.TestCase):
    def test_run54_boss_card_json_trailing_comma(self):
        payload = policy.parse_json_object(
            '{"deck_plan":{"offense":"A","defense":"B"},'
            '"scores":{"0":93,"1":89,"2":73,"3":18,"4":34},'
            '"reason":"Offering, has \\"quotes\\" and commas, inside",}'
        )
        self.assertEqual(payload["scores"]["0"], 93)
        self.assertIn("commas, inside", payload["reason"])

    def test_trailing_comma_in_nested_array_and_fenced(self):
        result = policy.parse_json_object(
            '```json\n{"scores":[1,2,],"description":"hello,} world",}\n```')
        self.assertEqual(result["scores"], [1, 2])
        self.assertEqual(result["description"], "hello,} world")

    def test_real_inherited_card_reward_route_selects_offering(self):
        # Exercise the actual v1.2 evaluator inherited by v1.7, not only
        # the standalone parser. No network, game or persistent data.
        agent = object.__new__(v17.ContinualC2Run55Agent)
        agent.use_llm = True
        agent._filter_human_forbidden_card_rewards = lambda gs, options: options
        agent._card_reward_prior_lines = lambda options: "Safe card priors."
        agent._load_persistent_deck_plan = lambda gs: {}
        agent._save_persistent_deck_plan = lambda *a, **kw: None
        agent.add_memory_to_prompt = lambda label, prompt, **kw: (prompt, "CARD_REWARD", [])
        agent.call_llm = lambda *args, **kw: (
            SimpleNamespace(output_text='{"deck_plan":{"offense":"direct"},'
                            '"scores":{"0":93,"1":34},"reason":"Offering",}'), 3.0)
        agent.get_usage = lambda response: (150, 40)
        agent.log_debug = lambda msg="": None
        events = []
        agent.log_run_event = lambda name, gs=None, **kw: events.append((name, kw))
        game = {"room_phase": "COMPLETE", "act": 1, "floor": 16,
                "current_hp": 15, "max_hp": 80, "act_boss": "Hexaghost",
                "deck": [], "relics": [], "keys": {}}
        options = [
            {"description": "Take Offering", "command": "CHOOSE 0"},
            {"description": "Skip this card reward", "command": "SKIP"},
        ]
        chosen = agent.choose_card_reward(game, options)
        self.assertEqual(chosen["description"], "Take Offering")
        record = [kw for kind, kw in events if kind == "LLM_CALL"][-1]
        self.assertFalse(record["fallback_used"])
        self.assertEqual(record["scores"]["0"], 93.0)

    def test_irrecoverable_json_rejected_no_fabricated_scores(self):
        with self.assertRaises((ValueError, json.JSONDecodeError)):
            policy.parse_json_object('{"scores":{"0":91,')
        with self.assertRaises((ValueError, json.JSONDecodeError)):
            policy.parse_json_object('not json')


class ContextPolicy(unittest.TestCase):
    def game(self):
        return {
            "current_hp": 12, "max_hp": 80,
            "combat_state": {
                "player": {"current_hp": 12, "max_hp": 80, "energy": 3},
                "monsters": [{"name": "Lagavulin", "intent": "UNKNOWN"}],
                "hand": [{"name": "Inflame"}, {"name": "Strike"}],
            },
            "deck": [],
            "relics": [],
        }

    def test_old_relevant_authoritative_rule_survives_recent_generic_rules(self):
        old = _rule("old_lagavulin", "With Lagavulin UNKNOWN intent, defend low HP.", run=12)
        unrelated = [
            _rule(f"generic_{n}", f"General rule number {n} about shop economy", run=40 + n)
            for n in range(20)
        ]
        selected, audit = policy.select_rules(unrelated + [old], "COMBAT", self.game())
        self.assertIn(old, selected)
        self.assertIn("old_lagavulin", audit["pinned_authoritative_ids"])
        self.assertLess(len(selected), len(unrelated) + 1)
        self.assertEqual(audit["candidate_count"], 21)

    def test_unknown_intent_teaching_not_dropped_by_entity_overflow(self):
        unrelated = [
            _rule(f"entity_{n}", f"Use Inflame against Lagavulin case {n}.", run=15 + n)
            for n in range(12)
        ]
        critical = _rule(
            "critical_unknown", "With UNKNOWN intent, missing incoming damage "
            "is not zero; prioritize survival at low HP.", run=54
        )
        selected, audit = policy.select_rules(
            unrelated + [critical], "COMBAT", self.game(), max_rules=8
        )
        self.assertIn(critical, selected)
        self.assertIn("critical_unknown", audit["pinned_authoritative_ids"])

    def test_context_retrieval_does_not_rewrite_memory(self):
        rule = _rule("abc", "Retain the exact human wording about Lagavulin", run=3)
        before = json.dumps(rule, sort_keys=True)
        selected, _ = policy.select_rules([rule], "COMBAT", self.game())
        self.assertEqual(json.dumps(rule, sort_keys=True), before)
        self.assertEqual(selected[0]["guidance"], rule["guidance"])

    def test_pinned_human_rules_override_soft_limit(self):
        pinned = [
            _rule(f"pinned_{n}", f"Against Lagavulin always assess risk {n}.", run=n + 1)
            for n in range(10)
        ]
        selected, audit = policy.select_rules(pinned, "COMBAT", self.game(), max_rules=8)
        self.assertEqual(len(selected), 10)
        self.assertTrue(audit["soft_limit_exceeded"])

    def test_missing_state_still_returns_deterministic_subset(self):
        items = [_rule(str(n), "Choose carefully", run=n) for n in range(15)]
        selected1, audit1 = policy.select_rules(items, "CARD_REWARD", None)
        selected2, audit2 = policy.select_rules(items, "CARD_REWARD", None)
        self.assertEqual(audit1, audit2)
        self.assertEqual(selected1, selected2)
        self.assertEqual(len(selected1), 8)

    def test_prompt_replacement_keeps_downstream_safety_text(self):
        agent = object.__new__(v17.ContinualC2Run55Agent)
        agent.playbook = {"updated_through_run": 54}
        agent.retrieve_memories = lambda category: [
            _rule(str(n), f"Teaching number {n} about Lagavulin", run=n)
            for n in range(1, 14)
        ]
        recorded = []
        agent.log_run_event = lambda typ, gs=None, **kw: recorded.append((typ, kw))

        def fake_legacy(self, decision_type, prompt, game_state=None,
                        memory_category=None, output_instruction=""):
            return (
                prompt +
                "\n\nSTATE-MATCHED AUTHORITATIVE HUMAN TEACHING — PINNED:"
                "\n<legacy pin>"
                "\n\nCUMULATIVE LEARNED POLICY — ALL APPLICABLE RULES:"
                "\n<all 49 old rules>"
                "\n\nDECISION AUTHORITY ORDER (highest to lowest):"
                "\n1. HUMAN TEACHING"
                "\n\nRUN49 X-COST RULE: retained",
                "COMBAT",
                [str(n) for n in range(1, 14)],
            )

        with patch.object(v17.v161.ContinualC2Run49Agent,
                          "add_memory_to_prompt", fake_legacy):
            result, category, ids = agent.add_memory_to_prompt(
                "COMBAT_PLAN_VERIFIER_V13", "Verifier base prompt",
                self.game(), "COMBAT"
            )
        self.assertNotIn("<all 49 old rules>", result)
        self.assertNotIn("<legacy pin>", result)
        self.assertIn("RUN49 X-COST RULE: retained", result)
        self.assertIn("DECISION AUTHORITY ORDER", result)
        self.assertIn("V1.7 CONDITIONAL TEACHING", result)
        self.assertEqual(ids, recorded[-1][1]["memory_ids"])
        self.assertEqual(recorded[-1][0], "MEMORY_RETRIEVAL")


class SafetyAndBoundary(unittest.TestCase):
    def test_unparseable_card_reward_pauses_before_returning_choice(self):
        agent = object.__new__(v17.ContinualC2Run55Agent)
        logged = []
        with patch.object(v17.v161.ContinualC2Run49Agent, "log_run_event",
                          lambda self, typ, gs=None, **kw: logged.append(typ)):
            with self.assertRaises(v17.base.ExperimentPausedError):
                agent.log_run_event(
                    "LLM_CALL", {}, decision_type="CARD_REWARD_EVALUATION_V12",
                    fallback_used=True, parse_error="invalid scores",
                )
        self.assertIn("RUN55_CARD_REWARD_PARSE_PAUSED", logged)

    def test_run54_requires_matching_review_playbook_event_and_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review = root / "review.json"
            book = root / "playbook.json"
            ledger = root / "events.jsonl"
            checkpoint = root / "baseline.zip"
            checkpoint.write_bytes(b"fixture")
            review.write_text(json.dumps({
                "status": "FINALIZED", "source_run": 54,
                "source_run_id": "run54", "review_decision": "HUMAN_TEACHING",
                "human_feedback": "Conditional survival feedback.",
            }))
            book.write_text('{"updated_through_run":54}')
            ledger.write_text(json.dumps({
                "event_type": "POST_RUN_REFLECTION_COMPLETE",
                "completed_run_number": 54, "reflected_run_id": "run54"
            }) + "\n")
            self.assertEqual(v17.verify_run54_cutover(
                ledger, book, review, checkpoint)["updated_through_run"], 54)
            checkpoint.unlink()
            with self.assertRaisesRegex(ValueError, "checkpoint missing"):
                v17.verify_run54_cutover(ledger, book, review, checkpoint)
            checkpoint.write_bytes(b"fixture")
            ledger.write_text("")
            with self.assertRaisesRegex(ValueError, "POST_RUN_REFLECTION_COMPLETE"):
                v17.verify_run54_cutover(ledger, book, review, checkpoint)

    def test_run54_freeze_is_write_once_with_full_local_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in freeze.REQUIRED:
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text("{}", encoding="utf-8")
            (root / "reflection/condition_c2_playbook.json").write_text(
                '{"updated_through_run":54}')
            (root / "reflection/condition_c2_outputs/run_54_feedback_review.json").write_text(
                json.dumps({"source_run": 54, "source_run_id": "r54",
                            "status": "FINALIZED", "review_decision": "HUMAN_TEACHING",
                            "human_feedback": "A lesson"}))
            (root / "spirecomm/run_events_c2.jsonl").write_text(
                json.dumps({"event_type": "RUN_END", "completed_run_number": 54,
                            "run_id": "r54"}) + "\n" +
                json.dumps({"event_type": "POST_RUN_REFLECTION_COMPLETE",
                            "completed_run_number": 54,
                            "reflected_run_id": "r54"}) + "\n")
            output = root / "frozen.zip"
            with patch.object(freeze, "PROJECT", root), patch.object(freeze, "TARGET", output):
                freeze.main()
                self.assertTrue(output.is_file())
                with self.assertRaisesRegex(SystemExit, "will not overwrite"):
                    freeze.main()

    def test_active_controller_binding(self):
        self.assertIs(v17.base.STSAgent, v17.ContinualC2Run55Agent)


if __name__ == "__main__":
    unittest.main(verbosity=2)
