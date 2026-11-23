"""Run 56 v1.7.1: decision-relevant retrieval and conservative lethal checks.

Pure helpers only. All Run 1-55 histories, memory and historical controllers
remain unchanged. This is intentionally NOT a complete STS damage simulator.
"""
from __future__ import annotations

import re
from typing import Any

import run55_policy as previous

BASIC_ATTACK_DAMAGE = {
    "Strike": 6, "Strike+": 9,
    "Bash": 8, "Bash+": 10,
    "Thunderclap": 4, "Thunderclap+": 7,
}
PASSIVE_ACTIONS = {"End turn", "Play Defend", "Play Defend+", "Play Trip"}
KNOWN_NON_DAMAGE_RELICS = {"Burning Blood", "Toy Ornithopter"}
KNOWN_PLAYER_POWERS = {
    "strength", "weak", "frail", "dexterity", "artifact", "vulnerable",
}


def _power_amount(powers: Any, name: str) -> int | None:
    """Return None if an observed power has an unusable amount."""
    rows = powers.values() if isinstance(powers, dict) else (powers or [])
    for row in rows:
        if not isinstance(row, dict):
            continue
        names = {str(row.get(k) or "").casefold()
                 for k in ("id", "name", "power_id")}
        if name.casefold() in names:
            try:
                return int(row.get("amount", 0))
            except (TypeError, ValueError):
                return None
    return 0


def optimistic_attack_ceiling(state: dict, descriptions: list[str]) -> dict | None:
    """Screen a claimed kill with an optimistic bound, never certify lethal.

    Apply negative Strength and allow a generous 2x multiplier for all known
    ordinary attacks. Unrecognized damage mechanics cause abstention. An upper
    bound below enemy HP disproves a kill; a larger bound proves nothing.
    """
    combat = (state or {}).get("combat_state") or {}
    player = combat.get("player") or {}
    monsters = [m for m in (combat.get("monsters") or [])
                if isinstance(m, dict) and not m.get("is_gone")
                and not m.get("half_dead")
                and int(m.get("current_hp") or 0) > 0]
    if len(monsters) != 1:
        return None
    enemy = monsters[0]
    powers = player.get("powers") or []
    rows = list(powers.values()) if isinstance(powers, dict) else powers
    if not isinstance(rows, list):
        return None
    if any(str(p.get("id") or p.get("name") or p.get("power_id") or "").casefold()
           not in KNOWN_PLAYER_POWERS for p in rows if isinstance(p, dict)):
        return None
    strength = _power_amount(powers, "Strength")
    if strength is None or strength >= 0:
        return None
    for relic in (state or {}).get("relics") or []:
        name = str(relic.get("name") or "") if isinstance(relic, dict) else str(relic)
        if name not in KNOWN_NON_DAMAGE_RELICS:
            return None
    cards = []
    for description in descriptions:
        desc = str(description or "")
        if desc in PASSIVE_ACTIONS:
            continue
        match = re.match(r"^Play (.+?) on ", desc)
        if not match or match.group(1) not in BASIC_ATTACK_DAMAGE:
            return None
        cards.append(match.group(1))
    if not cards:
        return None
    # Ignore enemy Block, Weak, and order of Vulnerable application in the
    # optimistic direction. Do not use this as an exact-damage simulator.
    upper = 2 * sum(max(0, BASIC_ATTACK_DAMAGE[name] + strength)
                    for name in cards)
    enemy_hp = int(enemy["current_hp"])
    return {
        "optimistic_damage_ceiling": upper,
        "enemy_hp": enemy_hp,
        "player_strength": strength,
        "attack_cards": cards,
        "claimed_lethal_disproved": upper < enemy_hp,
        "limitation": "known ordinary attacks only; optimistic not exact",
    }


def select_rules_v171(
    rules: list[dict], category: str, game_state: dict | None,
    max_rules: int = previous.MAX_CONTEXT_RULES,
) -> tuple[list[dict], dict]:
    """Retain pinned human teaching and promote actual decision-type lessons.

    The v1.7 hard pins are never discarded. Up to two corresponding-category
    lessons are kept if available, without rewriting the source playbook.
    """
    chosen, audit = previous.select_rules(rules, category, game_state, max_rules)
    category = str(category).upper()
    same = [rule for rule in rules
            if str(rule.get("category") or "").upper() == category]
    if not same:
        audit["decision_category_count"] = 0
        audit["decision_category_promoted"] = 0
        return chosen, audit

    choices = " ".join(str(choice) for choice in
                       ((game_state or {}).get("choice_list") or [])).casefold()
    option_tokens = previous._terms(choices)
    def rank(rule):
        words = previous._terms(
            str(rule.get("when") or "") + " " + str(rule.get("guidance") or ""))
        return (len(option_tokens & words),
                bool(rule.get("authoritative")),
                previous.source_run(rule),
                str(rule.get("rule_id") or ""))
    same.sort(key=rank, reverse=True)

    pinned = set(audit["pinned_authoritative_ids"])
    ids = {str(r.get("rule_id") or "") for r in chosen}
    target = min(2, len(same))
    current = sum(str(r.get("category") or "").upper() == category for r in chosen)
    promoted = 0
    for rule in same:
        if current >= target:
            break
        identifier = str(rule.get("rule_id") or "")
        if identifier in ids:
            continue
        replace_at = next(
            (i for i in range(len(chosen) - 1, -1, -1)
             if str(chosen[i].get("rule_id") or "") not in pinned
             and str(chosen[i].get("category") or "").upper() != category),
            None,
        )
        if replace_at is None:
            chosen.append(rule)  # preserve even if pinned rules exceed the cap
        else:
            ids.discard(str(chosen[replace_at].get("rule_id") or ""))
            chosen[replace_at] = rule
        ids.add(identifier)
        current += 1
        promoted += 1

    selected_ids = [str(r.get("rule_id") or "") for r in chosen]
    selected_set = set(selected_ids)
    audit.update(
        policy="v171-decision-category-anchors+v17-authoritative-pinning",
        selected_ids=selected_ids,
        selected_count=len(chosen),
        omitted_count=len(rules) - len(chosen),
        omitted_ids=[str(r.get("rule_id") or "") for r in rules
                     if str(r.get("rule_id") or "") not in selected_set],
        soft_limit_exceeded=len(chosen) > max_rules,
        decision_category_count=current,
        decision_category_promoted=promoted,
    )
    return chosen, audit
