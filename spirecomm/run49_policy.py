"""Run-49 v1.6.1 hotfix: equivalent card matching and zero-energy X-cost guard.

Separate from frozen v1.6.0 Run-48 sources. A queued attack retains the
original monster slot. Identical card copies can satisfy the same semantic
action; different costs, upgrades or other known effects cannot.
"""
from __future__ import annotations

from typing import Any

from run48_policy import (
    action_signature, bind_plan as bind_v160, parse_play_command,
    target_still_matches, ENERGY_CHANGERS,
)

# Exclude physical instance IDs: two equal physical cards are interchangeable.
# Include known mutable/damage/cost fields so non-equivalent copies are not.
CARD_EFFECT_FIELDS = (
    "name", "id", "type", "upgrades", "cost", "cost_for_turn",
    "base_damage", "base_block", "base_magic_number", "magic_number",
    "misc", "exhaust", "ethereal", "is_ethereal", "is_upgraded",
    "is_cost_modified", "is_cost_modified_for_turn",
    "free_to_play_once", "is_playable",
)
CARD_INSTANCE_FIELDS = ("uuid", "instance_id")


def card_effect_profile(card: dict[str, Any]) -> dict[str, Any]:
    return {key: card[key] for key in CARD_EFFECT_FIELDS if key in card}


def _card_at_command(state, command):
    parsed = parse_play_command(command)
    if parsed is None:
        return None
    hand = (((state or {}).get("combat_state") or {}).get("hand") or [])
    slot = parsed[0]
    if not 1 <= slot <= len(hand):
        return None
    card = hand[slot - 1]
    return card if isinstance(card, dict) else None


def bind_plan_v161(state, actions, indexes):
    bound = bind_v160(state, actions, indexes)
    for item, index in zip(bound, indexes):
        card = _card_at_command(state, actions[index].get("command"))
        if card is not None:
            item["card_effect_profile"] = card_effect_profile(card)
            for key in CARD_INSTANCE_FIELDS:
                if card.get(key) is not None:
                    item["card_instance_field"] = key
                    item["card_instance_value"] = card[key]
                    break
    return bound


def find_equivalent_bound_action(state, actions, bound):
    """Select one provably equivalent PLAY command, without changing targets.

    Equivalent physical copies share *all supplied semantic fields*.
    Where an original card snapshot is available it must still match. If
    the selected card had an instance UUID and it survived, prefer it.
    Unmatched/ambiguous different-effect copies trigger a safe replan.
    """
    valid, reason = target_still_matches(state, bound)
    if not valid:
        return None, reason, 0

    signature = bound.get("signature")
    target_slot = bound.get("target_slot")
    candidates = []
    for action in actions:
        if action_signature(action.get("description")) != signature:
            continue
        command = action.get("command")
        parsed = parse_play_command(command)
        if target_slot is not None:
            if parsed is None or parsed[1] != target_slot:
                continue
        elif parsed is not None and parsed[1] is not None:
            # An originally untargeted action must not acquire a target.
            continue
        candidates.append(action)

    if not candidates:
        return None, "original card action or target is no longer legal", 0
    if len(candidates) == 1:
        only = candidates[0]
        card = _card_at_command(state, only.get("command"))
        expected = bound.get("card_effect_profile")
        if expected is not None and (card is None or
                                     card_effect_profile(card) != expected):
            return None, "card effect changed since plan creation", 1
        return only, "unique legal card and exact original target", 1

    # Do not collapse a pair of visually identical non-card actions (such as
    # identical potion descriptions) into a guessed slot.
    if any(parse_play_command(a.get("command")) is None for a in candidates):
        return None, "multiple non-card actions; do not guess", len(candidates)

    details = []
    for action in candidates:
        card = _card_at_command(state, action.get("command"))
        if card is None:
            return None, "card instance not in current hand", len(candidates)
        details.append((action, card_effect_profile(card), card))
    expected = bound.get("card_effect_profile")
    if expected is not None:
        details = [x for x in details if x[1] == expected]
        if not details:
            return None, "original card effect profile no longer available", len(candidates)
    # A different-effect candidate is not interchangeable, even if the
    # selected subset matches the original: only choose matching effects.
    profiles = [x[1] for x in details]
    if any(profile != profiles[0] for profile in profiles[1:]):
        return None, "same-name cards have different known effects", len(candidates)

    instance_field = bound.get("card_instance_field")
    instance_value = bound.get("card_instance_value")
    if instance_field:
        same_instance = [x for x in details if x[2].get(instance_field) == instance_value]
        if len(same_instance) == 1:
            return same_instance[0][0], "exact original card instance and target", len(candidates)

    # No exact original instance, but every remaining candidate is equivalent.
    # Pick the lowest *current* hand slot, not a stale historical slot.
    details.sort(key=lambda x: (parse_play_command(x[0]["command"])[0],
                                str(x[0]["command"])))
    return details[0][0], "equivalent card copies, original target preserved", len(candidates)


def _relic_names(state):
    relics = (state or {}).get("relics") or []
    if isinstance(relics, dict):
        relics = list(relics.values())
    out = []
    for relic in relics:
        if isinstance(relic, str):
            out.append(relic.casefold())
        elif isinstance(relic, dict):
            out.append(str(relic.get("name") or relic.get("id") or "").casefold())
    return out


def reject_unfounded_zero_energy_whirlwind(state, actions, indexes,
                                            original_descriptions, rationale):
    """Guard verifier-only damage claims for a 0-energy Whirlwind replacement.

    Without Chemical X, Whirlwind plays zero hits at zero energy. A
    *clearly reasoned* attack-play relic trigger can still be worthwhile,
    so do not treat it as universally illegal or always useless.
    We conservatively reject a new zero-energy Whirlwind replacement
    of the original End-turn plan unless that non-damage value is cited.
    """
    original = [str(x).casefold() for x in original_descriptions or []]
    if "end turn" not in original or any("whirlwind" in x for x in original):
        return False, "not a verifier-only End turn to Whirlwind replacement"
    if "chemical x" in _relic_names(state):
        return False, "Chemical X may grant Whirlwind hits at zero energy"
    combat = (state or {}).get("combat_state") or {}
    player = combat.get("player") or {}
    energy = player.get("energy")
    if not isinstance(energy, (int, float)):
        return False, "energy unavailable; cannot prove zero hits"
    hand = combat.get("hand") or []
    explanation = str(rationale or "").casefold()
    for index in indexes:
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(actions):
            return False, "action indexes validated separately"
        parsed = parse_play_command(actions[index].get("command"))
        if parsed is None:
            continue
        slot = parsed[0]
        if not 1 <= slot <= len(hand):
            return False, "current card not available; validated separately"
        card = hand[slot - 1]
        name = str(card.get("name") or "").casefold()
        try:
            cost = int(card.get("cost_for_turn", card.get("cost")))
        except (TypeError, ValueError):
            return False, "dynamic card cost; cannot prove zero hits"
        if name in ("whirlwind", "whirlwind+") and int(energy) == 0:
            # Allow explicitly described non-damage attack-play triggers,
            # but not a rationale that wrongly claims positive damage.
            attack_trigger = any(w in explanation for w in (
                "kunai", "shuriken", "nunchaku", "ink bottle", "pen nib",
                "attack-play", "third attack", "play an attack"
            ))
            acknowledges_no_damage = any(w in explanation for w in (
                "zero damage", "0 damage", "no damage", "zero hits", "0 hits"
            ))
            if attack_trigger and acknowledges_no_damage:
                return False, "explicit non-damage attack-play trigger"
            return True, ("zero-energy Whirlwind cannot deal baseline damage "
                          "without Chemical X; verifier did not justify "
                          "a known non-damage benefit")
        if name in (x.casefold() for x in ENERGY_CHANGERS):
            return False, "dynamic energy gain prevents a zero-hit proof"
        if cost >= 0:
            energy -= cost
        elif name not in ("whirlwind", "whirlwind+"):
            return False, "earlier dynamic X-cost card prevents a zero-hit proof"
    return False, "no unsupported zero-energy Whirlwind replacement"
