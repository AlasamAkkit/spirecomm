"""Offline regression tests for review candidates and safe UI rendering.

Run from repository root:
    python -m unittest discover -s reflection/tests -p "test_*.py"

No OpenAI call, no CommunicationMod process, and no active memory changes.
"""
from __future__ import annotations

import os
import sys
import unittest
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reflection"))
from active_review import build_active_review
from feedback_app import render_review
from followup_reflection import append_final_lessons_idempotently, load_raw_memory


class ActiveReviewTests(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("C2_SKIP_AGENT_QUESTIONS")
        os.environ["C2_SKIP_AGENT_QUESTIONS"] = "1"

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("C2_SKIP_AGENT_QUESTIONS", None)
        else:
            os.environ["C2_SKIP_AGENT_QUESTIONS"] = self.previous

    def test_flags_are_unverified_and_agent_questions_can_be_disabled(self):
        events = [
            {"event_type": "ACTION", "decision_type": "COMBAT_DECISION",
             "decision_source": "LLM", "act": 2, "floor": 21,
             "selected_action": "End turn"},
            {"event_type": "COMBAT_PLAN_VERIFICATION_V13",
             "verifier_replaced_plan": True},
            {"event_type": "RUN_END", "act": 2, "floor": 21,
             "gold": 588, "result": "LOSS"},
        ]
        states = [
            {"room_phase": "COMBAT", "act": 2, "floor": 21, "hp": 50},
            {"room_phase": "COMBAT", "act": 2, "floor": 21, "hp": 20},
        ]
        result = build_active_review(events, states, "Test only.")
        ids = {f["id"] for f in result["diagnostic_flags"]}
        self.assertIn("gold-unspent", ids)
        self.assertIn("hp-2-21", ids)
        self.assertIn("verifier-interventions", ids)
        self.assertEqual([], result["agent_questions"])
        self.assertIsNone(result["question_generation_error"])

    def test_existing_review_packets_still_render(self):
        packet = {
            "source_run": 38, "status": "PENDING",
            "run_summary": {"result": "LOSS", "act": 2, "floor": 21},
            "initial_reflection": {"summary": "Sample", "lessons": []},
            "strategic_timeline": [], "key_events": [],
        }
        content = render_review(ROOT / "reflection" / "run_38_feedback_review.json", packet)
        self.assertIn("Run 38", content)
        self.assertIn("HUMAN_TEACHING", content)
        self.assertNotIn("q_decision_", content)

    def test_targeted_corrections_get_separate_idempotent_verbatim_memories(self):
        with tempfile.TemporaryDirectory() as root:
            memory = Path(root) / "memory.jsonl"
            initial = {
                "category": "COMBAT", "title": "Original",
                "situation": "At low HP", "lesson": "General teaching",
                "evidence_points": ["Run trace"], "reasoning": "Human review",
                "confidence": "high", "applies_to": ["COMBAT"],
                "authoritative": True,
                "human_feedback_verbatim": "General teaching",
            }
            correction = {
                **initial,
                "title": "Targeted action correction",
                "lesson": "Use Power Through before End turn.",
                "human_feedback_verbatim": "Use Power Through before End turn.",
            }
            first, _ = append_final_lessons_idempotently(
                reflection={"lessons": [initial]},
                completed_run_number=39, run_id="sample39",
                memory_file=memory, condition="C2",
                source_override="human_teaching_verbatim",
            )
            second, _ = append_final_lessons_idempotently(
                reflection={"lessons": [correction]},
                completed_run_number=39, run_id="sample39",
                memory_file=memory, condition="C2",
                source_override="human_teaching_verbatim",
                start_index=2,
            )
            self.assertEqual(first[0]["id"], "c2_run_39_01")
            self.assertEqual(second[0]["id"], "c2_run_39_02")
            self.assertEqual(second[0]["source"], "human_teaching_verbatim")
            self.assertEqual(second[0]["human_feedback_verbatim"],
                             "Use Power Through before End turn.")
            # Crash recovery may reapply the same append: it must not duplicate.
            append_final_lessons_idempotently(
                reflection={"lessons": [correction]},
                completed_run_number=39, run_id="sample39",
                memory_file=memory, condition="C2",
                source_override="human_teaching_verbatim",
                start_index=2,
            )
            self.assertEqual(len(load_raw_memory(memory)), 2)

    def test_question_text_is_escaped_and_answer_field_present(self):
        packet = {
            "source_run": 39, "status": "PENDING",
            "run_summary": {"result": "LOSS", "act": 2, "floor": 18},
            "initial_reflection": {"summary": "Sample", "lessons": []},
            "strategic_timeline": [], "key_events": [],
            "agent_questions": [{
                "id": "a0001", "act": 2, "floor": 18,
                "selected_action": "Buy <unsafe>",
                "question": "Was this wise?",
                "uncertainty": "No shop later",
                "assumption_to_verify": "Shop accessible",
                "alternatives": ["Leave"],
            }],
        }
        content = render_review(ROOT / "reflection" / "run_39_feedback_review.json", packet)
        self.assertIn("q_decision_a0001", content)
        self.assertIn("q_feedback_a0001", content)
        self.assertNotIn("Buy <unsafe>", content)
        self.assertIn("Buy &lt;unsafe&gt;", content)


if __name__ == "__main__":
    unittest.main()
