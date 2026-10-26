"""Run-43 evidence-led safeguards. Pure functions; never mutate raw teaching."""
from __future__ import annotations

from collections import Counter
import math
import re

OLD_RELIC_LESSON = "c2_run_01_01"
NEW_RELIC_LESSON = "c2_run_23_01"
SUPERSESSION_SCOPE = "NEOW_BLESSING"
CARD_DAMAGE = {"Strike": 6, "Strike+": 9, "Thunderclap": 4, "Thunderclap+": 7}
SAFE_ENEMY_POWERS = {"strength", "angry", "enrage", "vulnerable"}


def _sources(rule):
    return {str(value) for value in (rule.get("source_memory_ids") or [])}


def assert_relic_teaching_present(playbook):
    rules = [rule for rows in (playbook.get("categories") or {}).values()
             for rule in rows]
    old = [rule for rule in rules if OLD_RELIC_LESSON in _sources(rule)]
    new = [rule for rule in rules if NEW_RELIC_LESSON in _sources(rule)]
    if not old or not new:
        raise ValueError(
            "Run-43 active-policy migration requires both original Run-1 and "
            "corrective Run-23 human lessons in the cumulative playbook."
        )
    if not any(rule.get("authoritative") for rule in new):
        raise ValueError("The corrective Run-23 lesson must remain authoritative.")


def active_neow_rules(rules):
    """Supersede Run-1 teaching only at Neow; keep immutable histories intact."""
    if not any(NEW_RELIC_LESSON in _sources(rule) and
               rule.get("authoritative") for rule in rules):
        raise ValueError("Missing authoritative Run-23 correction at Neow.")
    return [rule for rule in rules if OLD_RELIC_LESSON not in _sources(rule)]


def is_starting_relic_swap(description):
    normalized = " ".join(str(description or "").lower().split())
    return "starting relic" in normalized and "boss relic" in normalized


def neow_eligible_actions(actions):
    """Never fabricate an action; if a swap is unavoidable, preserve legality."""
    non_swap = [a for a in actions if not is_starting_relic_swap(a.get("description"))]
    return non_swap if non_swap else list(actions)


def _play_card_name(description, hand_names):
    text = str(description or "")
    if not text.startswith("Play "):
        return None
    remainder = text[5:]
    for name in sorted(hand_names, key=len, reverse=True):
        if remainder == name or remainder.startswith(name + " on "):
            return name
    return None


def validate_replacement_sequence(game_state, actions, indexes):
    """Reject only demonstrably impossible energy/hand use. Unknown costs stay unknown."""
    combat = (game_state or {}).get("combat_state") or {}
    player = combat.get("player") or {}
    hand = [x for x in combat.get("hand", []) if isinstance(x, dict)]
    if not isinstance(player.get("energy"), (float, int)):
        return True, "energy unavailable"
    energy = int(player["energy"])
    counts = Counter(str(card.get("name")) for card in hand if card.get("name"))
    costs = {}
    for card in hand:
        name = str(card.get("name") or "")
        if not name:
            continue
        try:
            cost = int(card.get("cost"))
        except (ValueError, TypeError):
            cost = -1
        costs.setdefault(name, cost)
    for index in indexes:
        if not isinstance(index, int) or not 0 <= index < len(actions):
            return False, "out-of-range action"
        description = str(actions[index].get("description") or "")
        if not description.startswith("Play "):
            continue
        name = _play_card_name(description, counts)
        if name is None:
            # Could be a generated card or modded action; no proven hand match.
            continue
        counts[name] -= 1
        if counts[name] < 0:
            return False, "card used more often than present: " + name
        cost = costs.get(name, -1)
        if cost < 0:
            # X-cost and modded cost values require richer evaluation.
            return True, "unknown dynamic cost"
        energy -= cost
        if energy < 0:
            return False, "replacement exceeds available energy"
    return True, "within known energy and hand constraints"


def has_unknown_attack_intent(game_state):
    monsters = ((game_state or {}).get("combat_state") or {}).get("monsters") or []
    for monster in monsters:
        if monster.get("is_gone") or int(monster.get("current_hp") or 0) <= 0:
            continue
        if str(monster.get("intent") or "").upper() in {"", "DEBUG", "UNKNOWN", "NONE"}:
            return True
    return False


def _power_amount(powers, name):
    for power in powers or []:
        if not isinstance(power, dict):
            continue
        if str(power.get("id") or power.get("name") or "").casefold() == name:
            return int(power.get("amount") or 0)
    return 0


def provable_simple_lethal(game_state, descriptions):
    """Narrow lower-bound check: a single unprotected target, known basic attacks.

    No claims about arbitrary card effects, multi-target combat, hidden intents,
    statuses that modify damage, or complex relic interactions.
    """
    combat = (game_state or {}).get("combat_state") or {}
    monsters = [m for m in (combat.get("monsters") or [])
                if not m.get("is_gone") and int(m.get("current_hp") or 0) > 0]
    if len(monsters) != 1:
        return False
    enemy = monsters[0]
    player = combat.get("player") or {}
    powers = player.get("powers") or []
    if any(str(p.get("id") or p.get("name") or "").casefold() in
           {"weak", "confused"} for p in powers if isinstance(p, dict)):
        return False
    enemy_powers = enemy.get("powers") or []
    if any(str(p.get("id") or p.get("name") or "").casefold()
           not in SAFE_ENEMY_POWERS for p in enemy_powers if isinstance(p, dict)):
        return False
    strength = _power_amount(powers, "strength")
    vulnerable = _power_amount(enemy_powers, "vulnerable")
    hand = [x for x in combat.get("hand", []) if isinstance(x, dict)]
    names = [str(card.get("name")) for card in hand if card.get("name")]
    used = Counter()
    energy = int(player.get("energy") or 0)
    damage = 0
    for description in descriptions:
        name = _play_card_name(description, names)
        if name not in CARD_DAMAGE:
            return False
        used[name] += 1
        matches = [c for c in hand if c.get("name") == name]
        if used[name] > len(matches):
            return False
        card = matches[used[name] - 1]
        try:
            cost = int(card.get("cost"))
        except (TypeError, ValueError):
            return False
        if cost < 0:
            return False
        energy -= cost
        if energy < 0:
            return False
        base = max(0, CARD_DAMAGE[name] + strength)
        damage += math.floor(base * 1.5) if vulnerable > 0 else base
        if name.startswith("Thunderclap"):
            vulnerable = max(1, vulnerable)
    return damage >= int(enemy.get("current_hp") or 0) + max(0, int(enemy.get("block") or 0))
