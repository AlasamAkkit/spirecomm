"""Offline tests for the read-only supervisor human-feedback export."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from export_c2_supervisor_feedback import build_snapshot, markdown, write_snapshot

ROOT = Path(__file__).resolve().parents[1]


def feedback(run, decision, text=""):
    return {"source_run": run, "review_decision": decision, "human_feedback": text}


def human_memory(run, text, id="memory"):
    return {"source_run": run, "id": id, "authoritative": True,
            "human_feedback_verbatim": text, "category": "COMBAT",
            "applies_to": ["COMBAT"]}


class SnapshotTests(unittest.TestCase):
    def test_verbatim_original_and_targeted_no_duplicate(self):
        main = "Avoid taking damage.\nPlay the block card first."
        additional = "Account for negative Strength before claiming lethal."
        result = build_snapshot(
            [feedback(1, "HUMAN_TEACHING", main),
             feedback(2, "APPROVE_INITIAL")],
            [human_memory(1, main, "m1"),
             human_memory(2, additional, "m2"),
             human_memory(2, additional, "m3")],
            through_run=2, playbook_updated_through=2
        )
        self.assertEqual(result["human_teaching_run_count"], 1)
        self.assertEqual(result["approved_initial_run_count"], 1)
        self.assertEqual(result["additional_correction_count"], 1)
        correction = result["runs"][1]["additional_authoritative_corrections"][0]
        self.assertEqual(correction["source_memory_ids"], ["m2", "m3"])
        self.assertEqual(result["runs"][0]["human_feedback_verbatim"], main)
        rendered = markdown(result)
        self.assertIn("    Play the block card first.", rendered)
        self.assertIn("    Account for negative Strength", rendered)
        self.assertNotIn("source_run_id", rendered)

    def test_rejects_missing_or_duplicate_feedback(self):
        with self.assertRaisesRegex(ValueError, "Missing finalized"):
            build_snapshot([feedback(1, "APPROVE_INITIAL")], [],
                           through_run=2, playbook_updated_through=2)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            build_snapshot([feedback(1, "APPROVE_INITIAL")] * 2, [],
                           through_run=1, playbook_updated_through=1)

    def test_rejects_unfinalized_playbook_or_decisions(self):
        with self.assertRaisesRegex(ValueError, "Playbook updated only"):
            build_snapshot([feedback(1, "APPROVE_INITIAL")], [],
                           through_run=2, playbook_updated_through=1)
        with self.assertRaisesRegex(ValueError, "Unfinalized"):
            build_snapshot([feedback(1, "PENDING")], [],
                           through_run=1, playbook_updated_through=1)

    def test_rejects_obvious_sensitive_information(self):
        for sensitive in [
            "Please use C:\\Users\\Person\\Private\\file.txt",
            "api_key=examplevalue",
            "-----BEGIN PRIVATE KEY-----",
            "password: mysecret",
        ]:
            with self.subTest(text=sensitive), self.assertRaisesRegex(
                ValueError, "Potential sensitive"
            ):
                build_snapshot([feedback(1, "HUMAN_TEACHING", sensitive)], [],
                               through_run=1, playbook_updated_through=1)

    def test_only_outputs_sanitized_keys(self):
        private = {
            **feedback(1, "HUMAN_TEACHING", "Do not dilute the deck."),
            "source_run_id": "private-id",
            "packet_file": "C:\\Users\\Person\\Private\\packet.json",
            "stored_at": "private time",
        }
        snapshot = build_snapshot([private], [], through_run=1,
                                  playbook_updated_through=1)
        rendered = json.dumps(snapshot)
        self.assertNotIn("packet_file", rendered)
        self.assertNotIn("private-id", rendered)
        self.assertNotIn("C:\\", rendered)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            md, js = write_snapshot(out, snapshot)
            self.assertEqual(len(list(out.iterdir())), 2)
            self.assertEqual(js.read_text(encoding="utf-8").count(
                '"review_decision"'), 1)
            self.assertIn("Do not dilute the deck.", md.read_text())

    def test_frozen_repository_dataset_through_37(self):
        """Tests real historical schema but does not publish private files."""
        archive = ROOT / "spirecomm" / "runs" / "C2_through_run38_pre_A10"
        from export_c2_supervisor_feedback import load_jsonl
        rows = load_jsonl(archive / "condition_c2_feedback.jsonl")
        memory = load_jsonl(archive / "condition_c2_raw_memory.jsonl")
        playbook = json.loads(
            (archive / "condition_c2_playbook.json").read_text(encoding="utf-8")
        )
        self.assertEqual(playbook["updated_through_run"], 37)
        report = build_snapshot(
            rows, memory, through_run=37,
            playbook_updated_through=playbook["updated_through_run"],
        )
        self.assertEqual(len(report["runs"]), 37)
        self.assertGreater(report["human_teaching_run_count"], 0)
        self.assertEqual(report["human_teaching_run_count"] +
                         report["approved_initial_run_count"], 37)

    def test_cli_writes_publication_copy_not_active_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            src = root / "private-reflection"
            out = root / "supervisor-materials"
            src.mkdir()
            (src / "condition_c2_feedback.jsonl").write_text(
                json.dumps(feedback(1, "HUMAN_TEACHING",
                                    "Skip low-impact card rewards.")) + "\n",
                encoding="utf-8")
            (src / "condition_c2_raw_memory.jsonl").write_text(
                json.dumps(human_memory(1, "Skip low-impact card rewards.")) +
                "\n", encoding="utf-8")
            (src / "condition_c2_playbook.json").write_text(
                json.dumps({"updated_through_run": 1}), encoding="utf-8")
            contents_before = {
                p.name: p.read_bytes() for p in src.iterdir() if p.is_file()
            }
            cmd = [
                sys.executable, str(ROOT / "reflection" /
                                    "export_c2_supervisor_feedback.py"),
                "--through-run", "1", "--reflection-dir", str(src),
                "--output-dir", str(out),
            ]
            validation = subprocess.run(
                cmd + ["--validate-only"], capture_output=True, text=True)
            self.assertEqual(validation.returncode, 0, validation.stderr)
            self.assertFalse(out.exists())
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(list(out.iterdir())), 2)
            self.assertEqual(contents_before, {
                p.name: p.read_bytes() for p in src.iterdir() if p.is_file()
            })


if __name__ == "__main__":
    unittest.main(verbosity=2)
