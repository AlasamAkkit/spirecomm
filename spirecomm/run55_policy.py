"""Run-55 v1.7 pure helpers: transparent memory selection and strict JSON repair.

No deletion, rewriting or consolidation of the authoritative playbook takes place.
Importing this module makes no network calls and changes no local files.
"""
from __future__ import annotations

import json
import re
from typing import Any

MAX_CONTEXT_RULES = 8
STOPWORDS = frozenset({
    "about", "after", "again", "against", "always", "available", "before",
    "block", "card", "cards", "combat", "current", "damage", "deck", "defend",
    "enemy", "energy", "from", "have", "ironclad", "more", "must", "never",
    "only", "play", "player", "should", "strike", "than", "that", "their",
    "them", "there", "these", "this", "turn", "when", "with", "without",
})
GENERIC_ENTITY_NAMES = frozenset({
    "strike", "strike+", "defend", "defend+", "bash", "bash+",
    "ascender's bane", "skip", "end turn",
})


def parse_json_object(text: str) -> dict[str, Any]:
    """Repair only trailing commas OUTSIDE strings; reject other invalid JSON.

    This handles the actual Run-54 Offering response, whose final object
    member ended in a comma before the closing brace. Never invent values.
    """
    cleaned = str(text or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("JSON object delimiters missing")
    cleaned = cleaned[start:end + 1]

    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        chars = []
        quoted = escaped = False
        for i, ch in enumerate(cleaned):
            if quoted:
                chars.append(ch)
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    quoted = False
                continue
            if ch == '"':
                quoted = True
                chars.append(ch)
                continue
            if ch == ",":
                following = cleaned[i + 1:].lstrip()
                if following.startswith(("}", "]")):
                    continue
            chars.append(ch)
        value = json.loads("".join(chars))
    if not isinstance(value, dict):
        raise ValueError("Structured response is not a JSON object")
    return value


def source_run(rule: dict[str, Any]) -> int:
    numbers = [
        int(m.group(1))
        for item in rule.get("source_memory_ids") or []
        if (m := re.search(r"(?:^|_)run_(\d+)(?:_|$)", str(item)))
    ]
    return max(numbers, default=0)


def _terms(text: str) -> set[str]:
    return {
        t for t in re.findall(r"[a-z][a-z0-9]{3,}", str(text or "").casefold())
        if t not in STOPWORDS
    }


def _entities(game_state: dict[str, Any] | None) -> list[str]:
    state = game_state or {}
    combat = state.get("combat_state") or {}
    names: list[str] = []
    for entity in (combat.get("hand") or []) + (combat.get("monsters") or []):
        if isinstance(entity, dict) and entity.get("name"):
            names.append(str(entity["name"]))
    for entity in (state.get("relics") or []) + (state.get("deck") or []):
        if isinstance(entity, dict) and entity.get("name"):
            names.append(str(entity["name"]))
    for choice in state.get("choice_list") or []:
        names.append(str(choice))
    result = []
    for n in names:
        key = " ".join(n.casefold().split())
        if key and key not in GENERIC_ENTITY_NAMES and len(key) >= 4 and key not in result:
            result.append(key)
    return result


def select_rules(
    rules: list[dict[str, Any]],
    category: str,
    game_state: dict[str, Any] | None,
    max_rules: int = MAX_CONTEXT_RULES,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Deterministic, stable, explainable retrieval (no additional LLM call).

    Preserve any state-entity-matched authoritative teaching, then prioritize
    matching context and recent teaching. max_rules is a SOFT target: never
    discard a matching authoritative rule to meet an arbitrary token budget.
    """
    if max_rules < 1:
        raise ValueError("max_rules must be at least one")
    state = game_state or {}
    combat = state.get("combat_state") or {}
    player = combat.get("player") or {}
    hp = player.get("current_hp", state.get("current_hp"))
    maxhp = player.get("max_hp", state.get("max_hp"))
    low_hp = isinstance(hp, (int, float)) and isinstance(maxhp, (int, float)) and maxhp > 0 and hp / maxhp <= 0.35
    monsters = combat.get("monsters") or []
    unknown_intent = any(
        str(m.get("intent") or "").upper() in {"DEBUG", "UNKNOWN", "NONE", ""}
        for m in monsters if isinstance(m, dict) and not m.get("is_gone")
    )

    entities = _entities(state)
    context = set().union(*(_terms(n) for n in entities)) if entities else set()
    if low_hp:
        context |= {"survival", "lethal", "health", "mitigation", "potions"}
    if unknown_intent:
        context |= {"unknown", "uncertain", "intent", "risk"}
    if str(category).upper() == "CARD_REWARD":
        context |= {"reward", "dilution", "scaling", "synergy"}
    if str(category).upper() == "COMBAT":
        context |= {"survival", "lethal", "target", "sequence"}

    ranked = []
    for position, rule in enumerate(rules):
        content = " ".join(str(rule.get(k) or "") for k in ("guidance", "when"))
        content_lower = content.casefold()
        authority = bool(rule.get("authoritative"))
        matched_entities = [
            name for name in entities
            if re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", content_lower)
        ]
        overlap = len(context & _terms(content))
        latest = source_run(rule)
        # Reward current-state relevance first, then human authority, then recency.
        score = 12 * len(matched_entities) + min(overlap, 12) * 2
        score += 3 if authority else 0
        if low_hp and any(w in content_lower for w in ("low hp", "lethal", "surviv", "block", "heal")):
            score += 5
        if unknown_intent and any(w in content_lower for w in ("unknown", "uncertain", "intent")):
            score += 8
        score += min(latest // 12, 5)
        # Current named human teaching must not silently disappear.
        pinned = authority and bool(matched_entities)
        ranked.append((pinned, score, latest, -position, rule, matched_entities))

    pinned = [r for r in ranked if r[0]]
    pinned.sort(key=lambda r: (-r[1], -r[2], -r[3]))
    other = [r for r in ranked if not r[0]]
    other.sort(key=lambda r: (-r[1], -r[2], -r[3]))
    chosen = pinned + other[:max(0, max_rules - len(pinned))]
    ids = [str(x[4].get("rule_id") or "") for x in chosen]
    return [x[4] for x in chosen], {
        "policy": "v17-context-ranked-authoritative-entity-pinning",
        "category": str(category).upper(),
        "candidate_count": len(rules),
        "selected_count": len(chosen),
        "omitted_count": len(rules) - len(chosen),
        "selected_ids": ids,
        "omitted_ids": [str(r.get("rule_id") or "") for r in rules if str(r.get("rule_id") or "") not in ids],
        "pinned_authoritative_ids": [str(x[4].get("rule_id") or "") for x in pinned],
        "entity_names": entities,
        "soft_limit_exceeded": len(chosen) > max_rules,
        "low_hp": low_hp,
        "unknown_intent": unknown_intent,
    }


def format_selected_rules(rules: list[dict[str, Any]]) -> str:
    if not rules:
        return "V1.7 CONTEXT POLICY: No applicable lessons for this decision."
    parts = [
        "V1.7 CONTEXT-SELECTED CUMULATIVE HUMAN POLICY:",
        "The full original playbook is retained. These are the most applicable lessons now.",
        "Apply human guidance only when its conditions actually hold. Earlier card-order",
        "preferences do not override proven lethal or immediate survival without benefit.",
    ]
    for i, rule in enumerate(rules, 1):
        authority = "AUTHORITATIVE HUMAN" if rule.get("authoritative") else "LEARNED"
        parts.append(f"{i}. [{authority} | {rule.get('rule_id')} | source={','.join(str(x) for x in rule.get('source_memory_ids') or [])}]")
        when = str(rule.get("when") or "").strip()
        if when:
            parts.append("   When: " + when)
        parts.append("   Guidance: " + str(rule.get("guidance") or "").strip())
    return "\n".join(parts)
