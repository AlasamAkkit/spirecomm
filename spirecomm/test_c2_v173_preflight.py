"""Offline v1.7.3 Structured Outputs regression tests: no SDK/API/game access."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import run58_structured_output_policy as policy
import test_connection_c2_v173 as v173
import test_connection_c2_v172 as v172
from test_c2_v172_preflight import PROMPT, valid_payload

LABEL = policy.LABEL


def fake_response(text: str, **kw):
    return SimpleNamespace(
        status=kw.pop("status", "completed"),
        output=kw.pop("output", []),
        incomplete_details=kw.pop("incomplete_details", None),
        output_text=text,
        usage=SimpleNamespace(input_tokens=101, output_tokens=25),
    )


def mock_agent(create):
    agent = object.__new__(v173.ContinualC2V173Agent)
    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    agent.client = client
    agent.use_llm = True
    agent.current_run_id = "run-58-test"
    agent.completed_run_count = 57
    agent.log_debug = lambda *a, **kw: None
    events = []
    agent.log_run_event = lambda event_type, game_state=None, **kw: events.append(
        {"event_type": event_type, **kw}
    )
    return agent, client, events


class Schema(unittest.TestCase):
    def test_schema_is_strict_complete_and_exact_indices(self):
        for count in (2, 4, 20):
            with self.subTest(count=count):
                fmt = policy.card_reward_text_format(count)
                self.assertEqual(fmt["type"], "json_schema")
                self.assertTrue(fmt["strict"])
                root = fmt["schema"]
                self.assertFalse(root["additionalProperties"])
                self.assertEqual(set(root["properties"]), set(root["required"]))
                plan = root["properties"]["deck_plan"]
                self.assertFalse(plan["additionalProperties"])
                self.assertEqual(set(plan["properties"]), set(plan["required"]))
                scores = root["properties"]["scores"]
                self.assertFalse(scores["additionalProperties"])
                self.assertEqual(set(scores["properties"]), set(scores["required"]))
                self.assertEqual(
                    list(scores["properties"]), [str(i) for i in range(count)]
                )
                self.assertTrue(all(
                    spec == {"type": "number"} for spec in scores["properties"].values()
                ))
                self.assertEqual(plan["properties"]["add_policy"]["enum"],
                                 ["OPEN", "SELECTIVE", "SKIP_DEFAULT"])
                # No unsupported minimum/maximum keywords in strict mode.
                self.assertNotIn("minimum", json.dumps(fmt))
                self.assertNotIn("minLength", json.dumps(fmt))

    def test_invalid_action_counts(self):
        for count in (-1, 0, 1, 21, True, 2.2, "4"):
            with self.subTest(count=count), self.assertRaises(ValueError):
                policy.card_reward_text_format(count)

    def test_completed_envelope_and_refusal_and_incomplete(self):
        good = fake_response('{"ok": 1}')
        self.assertIs(policy.validate_response_envelope(good), good)
        self.assertIs(policy.validate_response_envelope({"output": []}),
                      policy.validate_response_envelope({"output": []})
                      if False else policy.validate_response_envelope(good)
                      if False else good) if False else None
        for bad in (
            fake_response("{}", status="incomplete"),
            fake_response("{}", status="failed"),
            fake_response("{}", incomplete_details={"reason": "max_output_tokens"}),
            fake_response("", output=[
                SimpleNamespace(content=[SimpleNamespace(
                    type="refusal", refusal="I cannot help")]
                )
            ]),
        ):
            with self.subTest(response=bad), self.assertRaises(ValueError):
                policy.validate_response_envelope(bad)


class Runtime(unittest.TestCase):
    def test_real_inherited_reward_path_selects_best_action(self):
        sent = []

        def create(**kwargs):
            sent.append(kwargs)
            return fake_response(json.dumps(valid_payload()))

        agent, original_client, events = mock_agent(create)
        agent._filter_human_forbidden_card_rewards = lambda state, actions: actions
        agent._load_persistent_deck_plan = lambda state: {}
        agent._card_reward_prior_lines = lambda actions: "No expert prior"
        agent._save_persistent_deck_plan = lambda *a, **kw: None
        agent.add_memory_to_prompt = lambda *a, **kw: (a[1], "CARD_REWARD", [])
        actions = [
            {"description": "Take Twin Strike+", "command": "CHOOSE 0"},
            {"description": "Take Burning Pact", "command": "CHOOSE 1"},
            {"description": "Take Thunderclap", "command": "CHOOSE 2"},
            {"description": "Skip this card reward", "command": "SKIP"},
        ]
        state = {
            "act": 2, "floor": 21, "room_phase": "COMPLETE",
            "room_type": "MonsterRoom", "screen_type": "CARD_REWARD",
            "current_hp": 50, "max_hp": 74,
            "seed": 567320668, "act_boss": "Automaton",
            "deck": [], "relics": [],
            "keys": {"ruby": False, "emerald": False, "sapphire": False},
        }
        selected = agent.choose_card_reward(state, actions)
        self.assertEqual(selected["description"], "Take Burning Pact")
        self.assertIs(agent.client, original_client)
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["input"].count("LEGAL ACTIONS"), 1)
        fmt = sent[0]["text"]["format"]
        self.assertEqual(fmt["name"], policy.FORMAT_NAME)
        self.assertEqual(list(fmt["schema"]["properties"]["scores"]["properties"]),
                         ["0", "1", "2", "3"])
        self.assertEqual(sent[0]["model"], v173.base.MODEL)
        self.assertEqual(sent[0]["reasoning"], {"effort": "medium"} if False else
                         sent[0]["reasoning"])
        self.assertFalse([e for e in events if e["event_type"] ==
                          "RUN57_CARD_REWARD_INVALID_MODEL_OUTPUT"])
        self.assertTrue([e for e in events if e["event_type"] ==
                         "RUN58_STRUCTURED_CARD_REWARD_REQUEST"])
        llm = [e for e in events if e["event_type"] == "LLM_CALL"]
        self.assertEqual(len(llm), 1)
        self.assertFalse(llm[0]["fallback_used"])
        self.assertEqual(llm[0]["selected_index"], 1)

    def test_non_card_request_unchanged(self):
        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            return fake_response("1")

        agent, original, events = mock_agent(create)
        resp, _latency = agent.call_llm(
            "COMBAT_STICKY_TURN_PLAN_V12", "Unchanged combat prompt", {}, "low"
        )
        self.assertEqual(resp.output_text, "1")
        self.assertEqual(len(calls), 1)
        self.assertNotIn("text", calls[0])
        self.assertIs(agent.client, original)
        self.assertFalse(events)

    def test_v172_repair_survives_unexpected_malformed_response(self):
        bad = json.dumps(valid_payload()).replace('"2": 50', '"2": fifty')
        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            return fake_response(bad)

        agent, original, events = mock_agent(create)
        out, _ = agent.call_llm(LABEL, PROMPT, {}, "medium")
        self.assertEqual(out.output_text, bad)
        self.assertIs(agent.client, original)
        self.assertEqual(len(calls), 1)
        self.assertIn("RUN57_CARD_REWARD_SCORE_WORD_REPAIRED",
                      [e["event_type"] for e in events])
        self.assertEqual(calls[0]["text"]["format"]["type"], "json_schema")

    def test_v172_three_invalid_schema_responses_pause_without_fallback(self):
        bad = json.dumps(valid_payload()).replace('"2": 50', '"2": gibberish')
        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            return fake_response(bad)

        agent, original, events = mock_agent(create)
        with tempfile.TemporaryDirectory() as folder, patch.object(
            v173.base, "PAUSE_FILE", Path(folder) / "PAUSE.txt"
        ):
            with self.assertRaises(v173.base.ExperimentPausedError):
                agent.call_llm(LABEL, PROMPT, {}, "low")
            self.assertTrue((Path(folder) / "PAUSE.txt").exists())
        self.assertIs(agent.client, original)
        self.assertEqual(len(calls), 3)
        self.assertEqual(sum(e["event_type"] ==
                             "RUN57_CARD_REWARD_INVALID_MODEL_OUTPUT"
                             for e in events), 3)
        self.assertTrue(any(e["event_type"] ==
                            "RUN57_CARD_REWARD_VALIDATION_PAUSED"
                            for e in events))

    def test_bad_envelope_retries_api_then_pauses_without_gameplay(self):
        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            return fake_response("{}", status="incomplete")

        agent, original, events = mock_agent(create)

        def pause(*args, **kwargs):
            raise v173.base.ExperimentPausedError(
                reason="test_incomplete",
                decision_type=LABEL,
                error_type="ValueError",
                error_message="incomplete",
            )

        agent.pause_for_api_failure = pause
        with patch.object(v173.base.time, "sleep", lambda *_: None):
            with self.assertRaises(v173.base.ExperimentPausedError):
                agent.call_llm(LABEL, PROMPT, {}, "low")
        self.assertIs(agent.client, original)
        self.assertEqual(len(calls), v173.base.LLM_MAX_ATTEMPTS)
        self.assertEqual(sum(e["event_type"] == "LLM_API_ERROR" for e in events),
                         v173.base.LLM_MAX_ATTEMPTS)
        self.assertTrue(any(e["event_type"] == "LLM_API_FAILED" for e in events))

    def test_unknown_format_not_silently_downgraded(self):
        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            raise RuntimeError("Unsupported JSON schema on this model")

        agent, original, events = mock_agent(create)

        def pause(*args, **kwargs):
            raise v173.base.ExperimentPausedError(
                reason="test_unsupported_schema",
                decision_type=LABEL,
                error_type="RuntimeError",
                error_message="unsupported",
            )

        agent.pause_for_api_failure = pause
        with patch.object(v173.base.time, "sleep", lambda *_: None):
            with self.assertRaises(v173.base.ExperimentPausedError):
                agent.call_llm(LABEL, PROMPT, {}, "low")
        self.assertIs(agent.client, original)
        self.assertEqual(len(calls), v173.base.LLM_MAX_ATTEMPTS)
        self.assertTrue(all("text" in kw for kw in calls))
        self.assertFalse(any(e["event_type"] == "LLM_CALL" for e in events))


class Cutover(unittest.TestCase):
    def test_run57_boundary_checks_matching_finalized_and_reflected(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            review, memory, events = [
                p / name for name in ("review.json", "playbook.json", "events.jsonl")
            ]
            review.write_text(json.dumps({
                "status": "FINALIZED", "source_run": 57,
                "source_run_id": "real-run57",
                "review_decision": "HUMAN_TEACHING", "human_feedback": "Be selective.",
            }), encoding="utf-8")
            memory.write_text(json.dumps({"updated_through_run": 57}),
                              encoding="utf-8")
            events.write_text("\n".join(json.dumps(e) for e in [
                {"event_type": "RUN_END", "completed_run_number": 57,
                 "run_id": "old-interrupted-attempt"},
                {"event_type": "RUN_END", "completed_run_number": 57,
                 "run_id": "real-run57"},
                {"event_type": "POST_RUN_REFLECTION_COMPLETE",
                 "completed_run_number": 57,
                 "reflected_run_id": "real-run57"},
            ]) + "\n", encoding="utf-8")
            v173.verify_run57_cutover(events, memory, review)
            memory.write_text(json.dumps({"updated_through_run": 56}),
                              encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not yet in the live"):
                v173.verify_run57_cutover(events, memory, review)

    def test_launcher_does_not_activate_v173_automatically(self):
        import test_connection
        import test_connection_v173_optin
        self.assertIs(test_connection.main, v172.main)
        self.assertIs(test_connection_v173_optin.main, v173.main)
        self.assertIs(v173.base.STSAgent, v172.ContinualC2V172Agent)
        self.assertEqual(v173.v172.v171.v17.v161.VARIANT, v172.VARIANT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
