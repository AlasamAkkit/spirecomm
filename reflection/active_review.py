"""Evidence-linked post-run diagnostic flags and optional agent questions.

This module never changes gameplay. Model-proposed questions are review
hypotheses, NOT factual error labels or authoritative human teaching.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Any


QUESTION_PROMPT = """You are helping a human teacher inspect an autonomous Slay the
Spire agent's COMPLETED run. Identify at most three CONSEQUENTIAL decisions
where the decision-making agent might reasonably ask a teacher whether its
choice was sound. Do NOT invent a doubt the acting model explicitly expressed:
these are POST-RUN questions. Only reference action_id values supplied below.
Distinguish evidence and assumptions. Do not conclude an action was wrong
merely because the run lost. Prefer decisions with meaningful alternatives,
survival consequences, deck-coherence risk, or contradictory prior plans.

Return JSON ONLY:
{"questions":[{"action_id":"a0001","question":"...?",
"uncertainty":"why the correct choice is unclear from available evidence",
"assumption_to_verify":"an assumption a teacher should check"}]}
If no grounded candidates are available return {"questions":[]}.
"""


def _eligible_actions(events: list[dict]) -> dict[str, dict]:
    """Stable, run-local link from review questions to logged action evidence."""
    actions = [
        row for row in events
        if row.get("event_type") == "ACTION"
        and row.get("decision_source") in {"LLM", "CONTROLLER"}
        and row.get("selected_action")
        and row.get("decision_type") not in {"START_RUN", "NEOW_TALK", "NEOW_LEAVE"}
    ]
    return {f"a{i:04d}": row for i, row in enumerate(actions, start=1)}


def _diagnostic_flags(events: list[dict], states: list[dict]) -> list[dict]:
    flags = []
    run_end = next((x for x in reversed(events) if x.get("event_type") == "RUN_END"), {})
    end_gold = run_end.get("gold")
    bought = any(
        row.get("event_type") == "ACTION"
        and row.get("decision_type") == "SHOP_DECISION"
        and "buy " in str(row.get("selected_action", "")).lower()
        for row in events
    )
    if isinstance(end_gold, (int, float)) and end_gold >= 250 and not bought:
        flags.append({
            "id": "gold-unspent",
            "title": "Unspent resources",
            "status": "CHECK",
            "act": run_end.get("act"), "floor": run_end.get("floor"),
            "evidence": f"Finished with {end_gold} gold and no logged shop purchase.",
            "assumption": "A useful shop route or purchase might have been available; map topology is not established here.",
        })

    # Compare actual observed HP, not hypothetical attack projections.
    by_room = defaultdict(list)
    for state in states:
        if state.get("room_phase") != "COMBAT":
            continue
        hp = state.get("hp")
        if not isinstance(hp, (int, float)):
            continue
        key = (state.get("act"), state.get("floor"))
        by_room[key].append(hp)
    drops = []
    for (act, floor), values in by_room.items():
        if not values:
            continue
        drop = max(values) - min(values)
        if drop >= 20:
            drops.append((drop, act, floor))
    for drop, act, floor in sorted(drops, reverse=True)[:3]:
        flags.append({
            "id": f"hp-{act}-{floor}",
            "title": "Large observed HP loss",
            "status": "CHECK",
            "act": act, "floor": floor,
            "evidence": f"Observed intra-encounter HP range spans {drop} HP.",
            "assumption": "Check whether the loss could be prevented; the trace alone does not prove a tactical mistake.",
        })

    replacements = [
        row for row in events
        if row.get("event_type") == "COMBAT_PLAN_VERIFICATION_V13"
        and row.get("verifier_replaced_plan") is True
    ]
    if replacements:
        flags.append({
            "id": "verifier-interventions",
            "title": "Combat-plan verifier interventions",
            "status": "CHECK",
            "act": None, "floor": None,
            "evidence": f"Verifier replaced {len(replacements)} combat plans during this run.",
            "assumption": "Replacements require case-by-case review and are not themselves errors.",
        })
    return flags[:6]


def _model_questions(action_map: dict[str, dict], trajectory: str) -> list[dict]:
    if os.environ.get("C2_SKIP_AGENT_QUESTIONS", "") == "1":
        return []
    # The reviewer is a separate post-run model call, not the acting agent.
    from openai import OpenAI
    actions = []
    for aid, row in action_map.items():
        if row.get("decision_type") not in {
            "COMBAT_DECISION", "CARD_REWARD_DECISION", "MAP_DECISION",
            "REST_DECISION", "BOSS_REWARD_DECISION", "SHOP_DECISION",
            "EVENT_DECISION", "SAPPHIRE_KEY_DECISION",
        }:
            continue
        actions.append({
            "action_id": aid,
            "act": row.get("act"), "floor": row.get("floor"),
            "decision_type": row.get("decision_type"),
            "selected_action": row.get("selected_action"),
            "alternatives": (row.get("legal_actions") or [])[:15],
            "hp": row.get("current_hp"), "max_hp": row.get("max_hp"),
        })
    # Keep last-act combat context and all strategic choices in the review.
    strategic = [x for x in actions if x["decision_type"] != "COMBAT_DECISION"]
    combats = [x for x in actions if x["decision_type"] == "COMBAT_DECISION"]
    context = (strategic[-95:] + combats[-65:])[-160:]
    client = OpenAI(timeout=90.0, max_retries=1)
    response = client.responses.create(
        model="gpt-5.6-luna",
        input=QUESTION_PROMPT + "\n\nRUN TRAJECTORY:\n"
        + trajectory[-15000:]
        + "\n\nINDEXED ACTION EVIDENCE:\n"
        + json.dumps(context, ensure_ascii=False),
    )
    raw = str(response.output_text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    payload = json.loads(raw)
    questions = payload.get("questions", [])
    if not isinstance(questions, list):
        return []
    valid_ids = {x["action_id"] for x in context}
    output = []
    for item in questions[:3]:
        if not isinstance(item, dict):
            continue
        aid = str(item.get("action_id", ""))
        question = str(item.get("question", "")).strip()
        if aid not in valid_ids or not question.endswith("?"):
            continue
        row = action_map[aid]
        output.append({
            "id": aid,
            "act": row.get("act"), "floor": row.get("floor"),
            "decision_type": row.get("decision_type"),
            "selected_action": row.get("selected_action"),
            "alternatives": row.get("legal_actions") or [],
            "question": question[:900],
            "uncertainty": str(item.get("uncertainty") or "")[:900],
            "assumption_to_verify": str(item.get("assumption_to_verify") or "")[:900],
            "source": "post_run_model_question_unverified",
        })
    return output


def build_active_review(
    events: list[dict], states: list[dict], trajectory: str
) -> dict[str, Any]:
    flags = _diagnostic_flags(events, states)
    action_map = _eligible_actions(events)
    result: dict[str, Any] = {
        "version": "active-review-v1",
        "diagnostic_flags": flags,
        "agent_questions": [],
        "question_generation_error": None,
    }
    try:
        result["agent_questions"] = _model_questions(action_map, trajectory)
    except Exception as exc:
        # Supplemental assistance must never block a completed-run review.
        result["question_generation_error"] = type(exc).__name__ + ": " + str(exc)[:220]
    return result
