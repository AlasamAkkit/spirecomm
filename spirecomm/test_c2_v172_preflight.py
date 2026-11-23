"""Offline regression suite for C2 v1.7.2 (no API/game calls)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import run57_reliability_policy as policy
import test_connection_c2_v172 as v172

PROMPT = (
    "You are evaluating a card reward.\nLEGAL ACTIONS\n"
    "0: Take Twin Strike+\n1: Take Burning Pact\n"
    "2: Take Thunderclap\n3: Skip this card reward\n\n"
    "STEP 1 — DECK PLAN FIRST\n"
)


def valid_payload():
    return {
        "deck_plan": {
            "offense": "Bash+ and upgraded attacks", "defense": "Block cards",
            "scaling": "Limited scaling", "draw_energy": "Offering and Pommel Strike",
            "aoe": "No reliable AoE", "weaknesses": ["Weak scaling"],
            "acquisition_priorities": ["Useful exhaust synergy"],
            "avoid": ["Redundant attack"], "add_policy": "SELECTIVE",
        },
        "plan_changed": False, "plan_change_reason": "No pivot",
        "scores": {"0": 46, "1": 74, "2": 50, "3": 62},
        "reason": "Burning Pact improves consistency",
    }


def response(raw):
    return SimpleNamespace(output_text=raw, usage=SimpleNamespace(
        input_tokens=123, output_tokens=45,
    ))


def agent_with_audit():
    agent = object.__new__(v172.ContinualC2V172Agent)
    agent.current_run_id = "test-run-57"
    agent.log_debug = lambda *a, **kw: None
    records = []
    agent.log_run_event = lambda event_type, game_state=None, **kw: records.append(
        {"event_type": event_type, **kw}
    )
    agent.get_usage = lambda resp: (123, 45)
    return agent, records


class Normalization(unittest.TestCase):
    def test_exact_run57_fifty_failure_is_repaired_only_in_scores(self):
        text = json.dumps(valid_payload()).replace('"2": 50', '"2":  fifty')
        fixed, repairs = policy.normalize_score_words(text)
        self.assertEqual(repairs, [{
            "index": "2", "original_word": "fifty", "number": 50,
        }])
        self.assertIn('"2":  50', fixed)
        self.assertEqual(policy.parse_card_reward_json(text)["scores"]["2"], 50)
        self.assertEqual(policy.validate_card_reward_payload(
            policy.parse_card_reward_json(text), 4)[1], 74)

    def test_does_not_change_narrative_or_unknown_word(self):
        p = valid_payload()
        p["reason"] = "There are fifty good reasons, perhaps"
        text = json.dumps(p).replace('"2": 50', '"2": nonsense')
        fixed, repairs = policy.normalize_score_words(text)
        self.assertEqual(fixed, text)
        self.assertEqual(repairs, [])
        self.assertRaises(ValueError, policy.parse_card_reward_json, text)

    def test_trailing_comma_repair_remains_supported(self):
        original = json.dumps(valid_payload())
        malformed = original[:-1] + ",}"
        self.assertEqual(policy.parse_card_reward_json(malformed)["scores"]["1"], 74)

    def test_validator_refuses_nonfinite_string_boolean_and_missing(self):
        for bad in ("NaN", float("inf"), True, "50"):
            p = valid_payload()
            p["scores"]["2"] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                policy.validate_card_reward_payload(p, 4)
        p = valid_payload()
        del p["scores"]["2"]
        with self.assertRaises(ValueError):
            policy.validate_card_reward_payload(p, 4)
        p = valid_payload()
        p["scores"]["4"] = 100
        with self.assertRaises(ValueError):
            policy.validate_card_reward_payload(p, 4)

    def test_validator_rejects_incomplete_deck_plan(self):
        p = valid_payload()
        del p["deck_plan"]["defense"]
        with self.assertRaises(ValueError):
            policy.validate_card_reward_payload(p, 4)

    def test_legal_action_count_uses_prompt_not_response(self):
        self.assertEqual(policy.legal_action_count(PROMPT), 4)
        with self.assertRaises(ValueError):
            policy.legal_action_count("No numbered actions")


class RetryLogic(unittest.TestCase):
    def test_repairs_run57_word_without_extra_call(self):
        agent, events = agent_with_audit()
        original = json.dumps(valid_payload()).replace('"2": 50', '"2": fifty')
        calls = []

        def fake_call(self, label, prompt, game_state=None, effort="low"):
            calls.append(prompt)
            return response(original), 100.0

        with patch.object(v172.v171.ContinualC2Run56Agent, "call_llm",
                          fake_call):
            result, latency = agent.call_llm(
                "CARD_REWARD_EVALUATION_V12", PROMPT, {}, "medium"
            )
        self.assertIs(result.output_text, original)
        self.assertEqual(len(calls), 1)
        self.assertEqual(latency, 100.0)
        self.assertEqual([e["event_type"] for e in events],
                         ["RUN57_CARD_REWARD_SCORE_WORD_REPAIRED"])

    def test_invalid_then_valid_retries_without_selecting_skip(self):
        agent, events = agent_with_audit()
        bad = json.dumps(valid_payload()).replace('"2": 50', '"2": maybe')
        good = json.dumps(valid_payload())
        responses = iter([response(bad), response(good)])
        sent = []

        def fake_call(self, label, prompt, game_state=None, effort="low"):
            sent.append(prompt)
            return next(responses), 250.0

        with patch.object(v172.v171.ContinualC2Run56Agent, "call_llm",
                          fake_call):
            result, _ = agent.call_llm(
                "CARD_REWARD_EVALUATION_V12", PROMPT, {}, "medium"
            )
        self.assertEqual(result.output_text, good)
        self.assertEqual(len(sent), 2)
        self.assertIn("The preceding card-reward JSON was rejected", sent[1])
        self.assertEqual(
            [e["event_type"] for e in events],
            ["RUN57_CARD_REWARD_INVALID_MODEL_OUTPUT",
             "RUN57_CARD_REWARD_RESPONSE_RECOVERED"],
        )
        self.assertEqual(events[0]["attempt"], 1)

    def test_three_invalid_responses_pause_with_marker_no_gameplay(self):
        agent, events = agent_with_audit()
        invalid = json.dumps(valid_payload()).replace('"2": 50', '"2": perhaps')
        calls = []

        def fake_call(self, label, prompt, game_state=None, effort="low"):
            calls.append(prompt)
            return response(invalid), 100.0

        with tempfile.TemporaryDirectory() as folder, \
             patch.object(v172.v171.ContinualC2Run56Agent, "call_llm",
                          fake_call), \
             patch.object(v172.base, "PAUSE_FILE", Path(folder) / "PAUSE.txt"):
            with self.assertRaises(v172.base.ExperimentPausedError):
                agent.call_llm(
                    "CARD_REWARD_EVALUATION_V12", PROMPT, {}, "medium"
                )
            self.assertIn("No gameplay choice was issued",
                          (Path(folder) / "PAUSE.txt").read_text())
        self.assertEqual(len(calls), 3)
        self.assertEqual(
            [e["event_type"] for e in events],
            ["RUN57_CARD_REWARD_INVALID_MODEL_OUTPUT"] * 3 +
            ["RUN57_CARD_REWARD_VALIDATION_PAUSED"],
        )
        self.assertTrue(all(e.get("no_gameplay_action_issued")
                            for e in events))

    def test_existing_combat_llm_is_not_modified(self):
        agent, _ = agent_with_audit()
        calls = []

        def fake_call(self, label, prompt, game_state=None, effort="low"):
            calls.append(label)
            return response("not JSON"), 5.0

        with patch.object(v172.v171.ContinualC2Run56Agent, "call_llm",
                          fake_call):
            returned, _ = agent.call_llm("COMBAT_STICKY_TURN_PLAN_V12", "X", {})
        self.assertEqual(returned.output_text, "not JSON")
        self.assertEqual(calls, ["COMBAT_STICKY_TURN_PLAN_V12"])


class ResearchAttribution(unittest.TestCase):
    def test_unfinished_run57_identified_without_marking_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            events = Path(folder) / "events.jsonl"
            events.write_text("\n".join([
                json.dumps({"event_type": "RUN_START", "run_id": "old-57",
                            "requested_seed": "123456789"}),
                json.dumps({"event_type": "RUN55_CARD_REWARD_PARSE_PAUSED",
                            "run_id": "old-57"}),
            ]) + "\n")
            old = policy.unfinished_attempt(events)
            self.assertEqual(old["run_id"], "old-57")
            self.assertEqual(old["reason"], "RUN55_CARD_REWARD_PARSE_PAUSED")
            with events.open("a") as stream:
                stream.write(json.dumps({
                    "event_type": "RUN57_PREVIOUS_ATTEMPT_INTERRUPTED",
                    "previous_run_id": "old-57"}) + "\n")
            self.assertIsNone(policy.unfinished_attempt(events))

    def test_completed_run_cannot_be_classified_unfinished(self):
        with tempfile.TemporaryDirectory() as folder:
            events = Path(folder) / "events.jsonl"
            events.write_text("\n".join([
                json.dumps({"event_type": "RUN_START", "run_id": "done"}),
                json.dumps({"event_type": "RUN_END", "run_id": "done"}),
            ]) + "\n")
            self.assertIsNone(policy.unfinished_attempt(events))

    def test_restart_marker_emitted_only_at_menu(self):
        agent, records = agent_with_audit()
        agent.current_run_id = None
        agent.completed_run_count = 56
        agent._v172_previous_unfinished = {
            "run_id": "old-57", "requested_seed": "123456789",
            "reason": "RUN55_CARD_REWARD_PARSE_PAUSED",
        }
        menu = {"in_game": False, "ready_for_command": True,
                "available_commands": ["start"], "game_state": {}}
        with patch.object(v172.v171.ContinualC2Run56Agent, "handle_state",
                          lambda self, state: "START COMMAND"):
            out = agent.handle_state(menu)
        self.assertEqual(out, "START COMMAND")
        self.assertEqual(records[0]["event_type"],
                         "RUN57_PREVIOUS_ATTEMPT_INTERRUPTED")
        self.assertEqual(records[0]["new_run_number"], 57)
        self.assertFalse(records[0]["counts_as_completed_run"])

    def test_existing_live_game_without_original_id_is_blocked(self):
        agent, events = agent_with_audit()
        agent.current_run_id = None
        with self.assertRaises(v172.base.ExperimentPausedError):
            agent.handle_state({"in_game": True, "game_state": {}})
        self.assertEqual(events[0]["event_type"],
                         "RUN57_UNATTACHED_LIVE_GAME_PAUSED")

    def test_launcher_and_historical_entrypoints(self):
        import test_connection
        self.assertIs(test_connection.main, v172.main)
        self.assertIs(v172.base.STSAgent, v172.ContinualC2V172Agent)
        self.assertEqual(v172.v171.v17.v161.VARIANT, v172.VARIANT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
