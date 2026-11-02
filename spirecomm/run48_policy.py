"""Run-48 v1.6 deterministic combat-plan feasibility and identity safeguards.

These checks are deliberately narrower than a full Slay the Spire simulator.
No historical controller or raw human feedback is modified.
"""
from __future__ import annotations

import re

PLAY = re.compile(r"^PLAY\s+(\d+)(?:\s+(\d+))?$", re.IGNORECASE)
POTION = re.compile(r"^POTION\s+use\s+(\d+)(?:\s+\d+)?$", re.IGNORECASE)
ENERGY_CHANGERS = {"Offering", "Offering+", "Seeing Red", "Seeing Red+",
                   "Bloodletting", "Bloodletting+", "Corruption", "Corruption+"}
DRAW_OR_RANDOM = {"Battle Trance", "Battle Trance+", "Pommel Strike",
                  "Pommel Strike+", "Warcry", "Warcry+", "Offering",
                  "Offering+", "Havoc", "Havoc+", "Infernal Blade",
                  "Infernal Blade+", "Distilled Chaos"}
UNKNOWN_INTENTS = {"", "DEBUG", "UNKNOWN", "NONE"}


def action_signature(description):
    text = str(description or "").casefold().strip()
    text = re.sub(r"\s*\(\s*\d+\s*hp\s*\)", "", text)
    return " ".join(text.split())


def parse_play_command(command):
    match = PLAY.fullmatch(str(command or "").strip())
    if not match:
        return None
    return int(match.group(1)), (int(match.group(2)) if match.group(2) is not None else None)


def validate_action_sequence(state, actions, indexes):
    """Prove impossible plans without assuming that card effects are static.

    A plan is rejected for impossible hand-instance reuse, energy deficit when
    no known energy modifier intervenes, nonexistent targets, or bad indexes.
    A current hand card may be selected once, not once per enemy target.
    """
    combat = (state or {}).get("combat_state") or {}
    hand = combat.get("hand") or []
    monsters = combat.get("monsters") or []
    player = combat.get("player") or {}
    energy = player.get("energy")
    if not isinstance(energy, (int, float)):
        energy = None
    used_cards = set()
    used_potions = set()
    ended = False
    for position, raw_index in enumerate(indexes):
        if isinstance(raw_index, bool) or not isinstance(raw_index, int):
            return False, "non-integer action index"
        if not 0 <= raw_index < len(actions):
            return False, "out-of-range action index"
        action = actions[raw_index]
        command = str(action.get("command") or "").strip()
        if ended:
            return False, "actions scheduled after End turn"
        if command.upper() == "END":
            ended = True
            continue
        parsed = parse_play_command(command)
        if parsed:
            hand_slot, monster_slot = parsed
            if not 1 <= hand_slot <= len(hand):
                return False, "selected card position is not in current hand"
            if hand_slot in used_cards:
                return False, "same physical hand card scheduled more than once"
            used_cards.add(hand_slot)
            card = hand[hand_slot - 1]
            if not isinstance(card, dict):
                return False, "malformed hand card"
            if monster_slot is not None:
                if not 0 <= monster_slot < len(monsters):
                    return False, "target slot outside current monster roster"
                target = monsters[monster_slot]
                if target.get("is_gone") or target.get("half_dead"):
                    return False, "target is already gone"
            name = str(card.get("name") or "").strip()
            try:
                cost = int(card.get("cost"))
            except (TypeError, ValueError):
                cost = -1
            if energy is not None and cost >= 0:
                energy -= cost
                if energy < 0:
                    return False, "plan exceeds current energy without a known source"
            elif cost < 0:
                energy = None
            if name in ENERGY_CHANGERS:
                # The energy from a card/relic interaction is dynamic. Do not
                # falsely reject subsequent actions on a static cost sum.
                energy = None
            continue
        potion_match = POTION.fullmatch(command)
        if potion_match:
            slot = int(potion_match.group(1))
            if slot in used_potions:
                return False, "same potion slot used twice"
            used_potions.add(slot)
    return True, "no demonstrably impossible action"


def bind_plan(state, actions, indexes):
    """Store stable monster slot and available instance identity for each step."""
    monsters = (((state or {}).get("combat_state") or {}).get("monsters") or [])
    result = []
    for index in indexes:
        action = actions[index]
        description = str(action.get("description") or "")
        item = {"description": description, "signature": action_signature(description)}
        parsed = parse_play_command(action.get("command"))
        if parsed and parsed[1] is not None:
            slot = parsed[1]
            monster = monsters[slot]
            item.update(
                target_slot=slot,
                target_name=str(monster.get("name") or ""),
                target_max_hp=monster.get("max_hp"),
                roster_size=len(monsters),
            )
            for key in ("uuid", "id", "instance_id"):
                if monster.get(key) is not None:
                    item["target_identity_field"] = key
                    item["target_identity_value"] = monster[key]
                    break
        result.append(item)
    return result


def target_still_matches(state, bound):
    if "target_slot" not in bound:
        return True, "non-targeted action"
    monsters = (((state or {}).get("combat_state") or {}).get("monsters") or [])
    slot = bound["target_slot"]
    if len(monsters) != bound.get("roster_size"):
        return False, "monster roster changed; replan instead of guessing target"
    if not 0 <= slot < len(monsters):
        return False, "original monster slot no longer exists"
    monster = monsters[slot]
    if monster.get("is_gone") or monster.get("half_dead"):
        return False, "intended monster has been defeated"
    if str(monster.get("name") or "") != bound.get("target_name"):
        return False, "monster at original slot has different name"
    if monster.get("max_hp") != bound.get("target_max_hp"):
        return False, "monster at original slot has different max HP"
    key = bound.get("target_identity_field")
    if key and monster.get(key) != bound.get("target_identity_value"):
        return False, "monster instance identity changed"
    return True, "original target still present"


def find_bound_action(state, actions, bound):
    valid, reason = target_still_matches(state, bound)
    if not valid:
        return None, reason
    candidates = []
    for action in actions:
        if action_signature(action.get("description")) != bound.get("signature"):
            continue
        if "target_slot" in bound:
            parsed = parse_play_command(action.get("command"))
            if not parsed or parsed[1] != bound["target_slot"]:
                continue
        candidates.append(action)
    if len(candidates) != 1:
        return None, ("ambiguous target match" if candidates else
                      "original targeted action is no longer legal")
    return candidates[0], "exact action/target match"


def _known_added_block(player, descriptions):
    """Use existing effective Frail/Dex block projection when available."""
    # Reuse the already loaded historical module; importing v1.3.1 anew
    # could rebind the live CommunicationMod entrypoint as a side effect.
    import test_connection_c2_run43 as run43
    return int(run43.a10.stable.v131.project_simple_block(
        player or {}, descriptions)["known_added_block"])


def unknown_intent_defense_regression(state, original_descriptions,
                                      replacement_descriptions):
    """Reject only demonstrable defensive regression under unknown intent.

    No claim that a target kill is guaranteed and no automatic zero damage
    assumption. An offense-to-offense replacement remains eligible.
    """
    combat = (state or {}).get("combat_state") or {}
    unknowns = [
        m for m in (combat.get("monsters") or [])
        if (not m.get("is_gone") and not m.get("half_dead")
            and int(m.get("current_hp") or 0) > 0
            and str(m.get("intent") or "").upper() in UNKNOWN_INTENTS)
    ]
    if not unknowns:
        return False, "no unknown live intent"
    player = combat.get("player") or {}
    original_block = _known_added_block(player, original_descriptions)
    replacement_block = _known_added_block(player, replacement_descriptions)
    if original_block > replacement_block:
        return True, (f"unknown intents remain; replacement loses "
                      f"{original_block - replacement_block} verified Block")
    return False, "unknown intent without a demonstrable defensive regression"
