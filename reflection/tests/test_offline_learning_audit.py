"""Tests for the read-only audit; no gameplay or network calls."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import offline_learning_audit as audit


def playbook():
    return {"updated_through_run":52,"categories":{
        "COMBAT":[
            {"rule_id":"a","category":"COMBAT","applies_to":["COMBAT"],
             "guidance":"Preserve HP by choosing enough Block during dangerous elite attacks.",
             "authoritative":True,"source_memory_ids":["c2_run_50_01"]},
            {"rule_id":"b","category":"COMBAT","applies_to":["COMBAT"],
             "guidance":"Preserve HP by choosing enough Block during dangerous elite attacks.",
             "authoritative":True,"source_memory_ids":["c2_run_52_01"]}],
        "GENERAL":[{"rule_id":"c","category":"GENERAL",
                    "applies_to":["GENERAL"],
                    "guidance":"Keep starting Burning Blood relic.","source_memory_ids":[]}]
    }}


class LearningAuditTests(unittest.TestCase):
    def test_general_scope_is_active_in_combat(self):
        self.assertEqual(audit.audit_playbook(playbook())["applicable_counts"]["COMBAT"],3)

    def test_flags_duplicates_without_rewriting(self):
        source=playbook()
        old=json.dumps(source)
        result=audit.audit_playbook(source)
        self.assertEqual(result["authoritative_rules"],2)
        self.assertEqual(result["possible_repeats"][0]["type"],"exact")
        self.assertEqual(old,json.dumps(source))

    def test_source_coverage_reports_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/"raw.jsonl"
            file.write_text('{"id":"c2_run_50_01"}\n{"id":"missing"}\n')
            result=audit.memory_coverage(audit.flatten(playbook()),file)
            self.assertEqual(result["uncovered_ids"],["missing"])

    def test_shadow_preview_only_no_changes(self):
        pb=playbook()
        old=json.dumps(pb)
        events=[{"event_type":"MEMORY_RETRIEVAL","memory_category":"COMBAT",
                 "floor":7,"state_entities":["Lagavulin","Burning Blood"]}]
        out=audit.shadow_preview(pb,events,7,limit=1)
        self.assertFalse(out["modifies_controller"])
        self.assertEqual(out["total_applicable"],3)
        self.assertEqual(len(out["other_rule_ids_preserved"]),2)
        self.assertEqual(json.dumps(pb),old)

    def test_detects_incorrect_lagavulin_entry_hp_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)
            (path/"run_53_initial_reflection.json").write_text(
                '{"summary":"Entering Lagavulin with too little effective HP."}')
            (path/"run_53_states.json").write_text(json.dumps([{
                "hp":74,"max_hp":74,
                "combat":{"monsters":[{"name":"Lagavulin"}]}
            }]))
            self.assertEqual(audit._reflection_flags(path,53)[0]["observed_entry_hp"],74)

    def test_run_stats_exclude_verifier_input_tokens(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)
            entries=[
                {"event_type":"LLM_CALL","decision_type":"COMBAT_STICKY_TURN_PLAN_V12",
                 "input_tokens":22000,"prompt_characters":110000},
                {"event_type":"LLM_CALL","decision_type":"COMBAT_PLAN_VERIFIER_V13",
                 "input_tokens":94000,"prompt_characters":300000},
                {"event_type":"RUN_END","floor":7,"score":59,"result":"LOSS"}]
            (path/"run_53_raw.json").write_text(json.dumps(entries))
            x=audit.run_audit(path,53,53)[0]
            self.assertEqual(x["acting_combat_calls"],1)
            self.assertEqual(x["mean_acting_combat_input_tokens"],22000)

    def test_cli_writes_only_new_report_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            pb=root/"playbook.json"
            src=json.dumps(playbook())
            pb.write_text(src)
            memory=root/"raw.jsonl"
            memory.write_text('{"id":"c2_run_50_01"}\n')
            args=["--playbook",str(pb),"--raw-memory",str(memory),
                  "--runs-dir",str(root),"--output",str(root/"report.json")]
            self.assertEqual(audit.main(args),0)
            self.assertEqual(pb.read_text(),src)
            self.assertTrue((root/"report.json").exists())
            with self.assertRaises(SystemExit):
                audit.main(args)
            with self.assertRaises(SystemExit):
                audit.main(args[:-1]+[str(pb)])


if __name__=="__main__":
    unittest.main(verbosity=2)
