"""Read-only continual-C2 learning audit and offline relevance preview.

Never imports or changes the game controller, active playbook, raw memory,
reviews, or event log. Writes only to a new, explicitly requested report path.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter
from pathlib import Path

_STOP = {"about","after","always","before","card","cards","could","current",
         "during","every","from","have","instead","more","never","only",
         "should","their","then","there","this","when","where","while","with"}


def _words(s):
    return {w for w in re.findall(r"[a-z]{4,}", str(s).lower()) if w not in _STOP}


def flatten(playbook):
    categories = playbook.get("categories")
    if not isinstance(categories, dict):
        raise ValueError("Playbook must contain categories object")
    rules = []
    for category, group in sorted(categories.items()):
        if not isinstance(group, list):
            raise ValueError("Invalid rule category " + category)
        for index, row in enumerate(group, 1):
            if not isinstance(row, dict):
                raise ValueError("Invalid playbook rule")
            copy = dict(row)
            copy.setdefault("category", category)
            copy.setdefault("rule_id", "audit_" + category + "_" + str(index))
            rules.append(copy)
    return rules


def applies(rule, category):
    """Matches the deployed retrieve_memories scope logic."""
    scope = [str(s).upper() for s in
             (rule.get("applies_to") or [rule.get("category")])]
    return category.upper() in scope or "GENERAL" in scope


def repetition(rules):
    pairs = []
    for i, a in enumerate(rules):
        atext = str(a.get("guidance") or "").strip().lower()
        if len(atext) < 32:
            continue
        aw = _words(atext)
        for b in rules[i+1:]:
            btext = str(b.get("guidance") or "").strip().lower()
            if len(btext) < 32:
                continue
            bw = _words(btext)
            exact = atext == btext
            overlap = len(aw & bw) / max(1, len(aw | bw))
            if exact or (min(len(aw), len(bw)) >= 7 and overlap >= 0.82):
                pairs.append({
                    "rules": [a["rule_id"], b["rule_id"]],
                    "similarity": round(overlap, 3),
                    "type": "exact" if exact else "lexical_near_repeat",
                    "human_review_required": True})
    return pairs


def memory_coverage(rules, path):
    covered = {str(x) for r in rules for x in
               (r.get("source_memory_ids") or [])}
    result = {"covered_count": len(covered), "raw_count": None,
              "uncovered_ids": None}
    if path is None or not Path(path).is_file():
        return result
    raw = set()
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                if item.get("id"):
                    raw.add(str(item["id"]))
    result.update(raw_count=len(raw), uncovered_ids=sorted(raw - covered))
    return result


def audit_playbook(playbook, raw_memory=None):
    rules = flatten(playbook)
    categories = ["COMBAT","CARD_REWARD","REST","MAP","SHOP","EVENT",
                  "POTION","BOSS_REWARD","GENERAL"]
    return {
        "updated_through_run": playbook.get("updated_through_run"),
        "total_rules": len(rules),
        "primary_categories": dict(Counter(
            str(r["category"]).upper() for r in rules)),
        "applicable_counts": {
            c: sum(applies(r, c) for r in rules) for c in categories},
        "authoritative_rules": sum(bool(r.get("authoritative")) for r in rules),
        "authoritative_verbatim_characters": sum(
            len(str(r.get("guidance") or "")) for r in rules
            if r.get("authoritative")),
        "max_guidance_characters": max(
            (len(str(r.get("guidance") or "")) for r in rules), default=0),
        "broad_scope_rule_ids": [
            r["rule_id"] for r in rules if len(set(
                r.get("applies_to") or [r["category"]])) >= 5],
        "possible_repeats": repetition(rules)[:40],
        "memory_source_coverage": memory_coverage(rules, raw_memory),
        "conflict_caveat": (
            "Possible repetition does not prove conflict. "
            "Do not automatically delete, rewrite, or consolidate human teaching."),
    }


def _mean(values):
    return round(statistics.mean(values), 1) if values else None


def _reflection_flags(run_dir, number):
    path = Path(run_dir) / f"run_{number:02d}_initial_reflection.json"
    state_file = Path(run_dir) / f"run_{number:02d}_states.json"
    if not path.is_file() or not state_file.is_file():
        return []
    text = str(json.loads(path.read_text(encoding="utf-8")).get("summary") or "").lower()
    if not ("lagavulin" in text and ("entering" in text or "entered" in text)
            and ("too little" in text or "low hp" in text)):
        return []
    states = json.loads(state_file.read_text(encoding="utf-8"))
    for state in states:
        enemies = ((state.get("combat") or {}).get("monsters") or [])
        if any("lagavulin" in str(m.get("name","")).lower()
               for m in enemies if isinstance(m, dict)):
            hp, maximum = state.get("hp"), state.get("max_hp")
            if (isinstance(hp, (int,float)) and
                    isinstance(maximum, (int,float)) and maximum > 0
                    and hp/maximum >= 0.85):
                return [{"flag": "possible_incorrect_low_hp_entry_claim",
                         "observed_entry_hp": hp,
                         "observed_entry_max_hp": maximum,
                         "needs_human_check": True}]
            break
    return []


def run_audit(run_dir, first, last):
    rows = []
    for run in range(first, last+1):
        path = Path(run_dir) / f"run_{run:02d}_raw.json"
        if not path.is_file():
            rows.append({"run":run,"status":"snapshot_missing"})
            continue
        events = json.loads(path.read_text(encoding="utf-8"))
        end = next((e for e in reversed(events)
                    if e.get("event_type")=="RUN_END"), {})
        actor = [e for e in events if e.get("event_type")=="LLM_CALL"
                 and e.get("decision_type")=="COMBAT_STICKY_TURN_PLAN_V12"]
        memory = [e for e in events if e.get("event_type")=="MEMORY_RETRIEVAL"
                  and e.get("memory_category")=="COMBAT"]
        rows.append({
            "run":run,"floor":end.get("floor"),"score":end.get("score"),
            "result":end.get("result"),
            "controller":end.get("controller_variant"),
            "acting_combat_calls":len(actor),
            "mean_acting_combat_input_tokens":_mean([
                e["input_tokens"] for e in actor
                if isinstance(e.get("input_tokens"),(int,float))]),
            "mean_acting_combat_prompt_chars":_mean([
                e["prompt_characters"] for e in actor
                if isinstance(e.get("prompt_characters"),(int,float))]),
            "max_combat_rules_retrieved":max(
                (e.get("memory_count") or 0 for e in memory),default=0),
            "max_pinned_authoritative_rules":max(
                (e.get("pinned_authoritative_rule_count") or 0
                 for e in memory),default=0),
            "omitted_memory_events":sum(
                (e.get("omitted_memory_count") or 0) for e in memory),
            "reflection_flags":_reflection_flags(run_dir,run),
        })
    return rows


def shadow_preview(playbook, events, floor, limit=8):
    """Candidate attention diagnostic only; never changes live retrieval."""
    states = [e for e in events if e.get("event_type")=="MEMORY_RETRIEVAL"
              and e.get("memory_category")=="COMBAT" and e.get("floor")==floor]
    if not states:
        return {"status":"no_combat_memory_event","floor":floor}
    entities = sorted(set(str(x).lower() for x in
                          states[0].get("state_entities") or [] if len(str(x))>=4))
    eligible = [r for r in flatten(playbook) if applies(r,"COMBAT")]
    ranked = []
    for rule in eligible:
        text = (str(rule.get("when") or "")+" "+
                str(rule.get("guidance") or "")).lower()
        matched = [e for e in entities if e in text]
        ranked.append({
            "rule_id":rule["rule_id"],
            "score":5*len(matched)+2*bool(rule.get("authoritative")),
            "matched_entities":matched,
            "source_memory_ids":rule.get("source_memory_ids") or [],
            "authoritative":bool(rule.get("authoritative")),
        })
    ranked.sort(key=lambda r:(-r["score"],str(r["rule_id"])))
    return {
        "status":"offline_shadow_preview_only","floor":floor,
        "total_applicable":len(eligible),"entity_names":entities,
        "attention_candidates":ranked[:limit],
        "other_rule_ids_preserved":[r["rule_id"] for r in ranked[limit:]],
        "modifies_controller":False,
        "limitation":"Entity matching is only a heuristic, not proof of relevance.",
    }


def build_report(playbook, raw_memory, run_dir, first, last, preview_run, preview_floor):
    pb = json.loads(Path(playbook).read_text(encoding="utf-8"))
    report = {
        "schema":"continual-c2-offline-audit-v1",
        "read_only":True,"modifies_controller":False,
        "playbook":audit_playbook(pb,raw_memory),
        "runs":run_audit(run_dir,first,last),
    }
    if preview_run is not None:
        path = Path(run_dir)/f"run_{preview_run:02d}_raw.json"
        report["shadow_preview"] = (
            shadow_preview(pb,json.loads(path.read_text(encoding="utf-8")),
                           preview_floor) if path.is_file()
            else {"status":"run_snapshot_missing","run":preview_run})
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--playbook",default="reflection/condition_c2_playbook.json")
    parser.add_argument("--raw-memory",default="reflection/condition_c2_raw_memory.jsonl")
    parser.add_argument("--runs-dir",default="reflection/condition_c2_outputs")
    parser.add_argument("--first-run",type=int,default=48)
    parser.add_argument("--last-run",type=int,default=53)
    parser.add_argument("--preview-run",type=int,default=53)
    parser.add_argument("--preview-floor",type=int,default=7)
    parser.add_argument("--output",type=Path)
    a=parser.parse_args(argv)
    if a.first_run>a.last_run:
        parser.error("first-run must not exceed last-run")
    report=build_report(a.playbook,a.raw_memory,a.runs_dir,
                        a.first_run,a.last_run,a.preview_run,a.preview_floor)
    output=json.dumps(report,ensure_ascii=False,indent=2)+"\n"
    if a.output:
        target=a.output.resolve()
        blocked={Path(a.playbook).resolve(),Path(a.raw_memory).resolve()}
        blocked.update((Path(a.runs_dir)/f"run_{i:02d}_feedback_review.json").resolve()
                       for i in range(a.first_run,a.last_run+1))
        if target in blocked or target.exists():
            parser.error("Refusing to overwrite a live or existing file")
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(output,encoding="utf-8")
        print("Wrote read-only audit:",target)
    else:
        print(output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
