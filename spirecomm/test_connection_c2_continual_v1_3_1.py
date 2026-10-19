from __future__ import annotations

import importlib.util
import math
import re
from pathlib import Path

# ==============================================================
# C2 CONTINUAL v1.3.1 — POWER-AWARE BLOCK VERIFICATION
# ==============================================================
# Intervention boundary: Run 36 onward, after Run 35 was fully
# finalized/frozen under v1.3.0.
#
# v1.3.1 retains the complete cumulative playbook, the v1.3.0
# card/deck planner, and the second-pass combat verifier. It adds
# a deterministic, auditable projection of straightforward printed
# Block cards with known Frail/Dexterity modifiers, presented to
# BOTH combat planner and verifier. The result is a static projection,
# NOT a complete game simulator: enemy kills, Weak, relic triggers,
# potions, dynamic card effects and unrecognized effects may change it.
# The controller never silently substitutes an invented exact number.
#
# The Run-35 issue was an overestimate of +13 Block at the Collector:
# printed Shrug It Off+ (11), Impervious (30), and Defend+ (8)
# total 49, but under Frail they yield 8+22+6 = 36.

CONTROLLER_VERSION = "c2-continual-teaching-v1.3.1-block-aware-verifier"
INTERVENTION_START_RUN = 36
PREVIOUS_COMPLETED_RUN = 35
DECISION_ARCHITECTURE = "cumulative-policy+context-pinning+persistent-deck-plan+block-aware-verified-sticky-turn-plan-v1"
MEMORY_POLICY = "all_applicable_rules_no_topk_with_context_pinning_v1"

BASE_DIR = Path(__file__).resolve().parent
V130 = BASE_DIR / "test_connection_c2_continual_v1_3.py"
if not V130.is_file():
    raise FileNotFoundError(f"Missing historical v1.3.0 controller: {V130}")

_spec = importlib.util.spec_from_file_location("_c2_continual_v130", V130)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Could not load historical v1.3.0 controller.")
v130 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v130)

# New run events must identify the new controller, but historical
# controller source files and previously recorded events stay unchanged.
v130.CONTROLLER_VERSION = CONTROLLER_VERSION
v130.DECISION_ARCHITECTURE = DECISION_ARCHITECTURE
v130.INTERVENTION_START_RUN = INTERVENTION_START_RUN
v130.v121.CONTROLLER_VERSION = CONTROLLER_VERSION
v130.v121.DECISION_ARCHITECTURE = DECISION_ARCHITECTURE
v130.v121.v120.CONTROLLER_VERSION = CONTROLLER_VERSION
v130.v121.v120.DECISION_ARCHITECTURE = DECISION_ARCHITECTURE
v130.v121.v120.INTERVENTION_START_RUN = INTERVENTION_START_RUN
v130.v121.v120.v112.CONTROLLER_VERSION = CONTROLLER_VERSION
v130.v121.v120.v112.v111.CONTROLLER_VERSION = CONTROLLER_VERSION
v130.v121.v120.v112.v111.v11.CONTINUAL_CONTROLLER_VERSION = CONTROLLER_VERSION
v130.v121.v120.v112.v111.v11.prior.CONTINUAL_CONTROLLER_VERSION = CONTROLLER_VERSION

base = v130.base
ParentAgent = v130.ContinualC2V13Agent

# Base printed Block only, before Dexterity and Frail. A value absent
# from this dictionary is deliberately UNKNOWN. This is not a card tier
# policy and imposes no new card selection preference.
_STATIC_PRINTED_BLOCK = {
    "Defend": 5,
    "Defend+": 8,
    "Shrug It Off": 8,
    "Shrug It Off+": 11,
    "Ghostly Armor": 10,
    "Ghostly Armor+": 13,
    "Impervious": 30,
    "Impervious+": 40,
    "Flame Barrier": 12,
    "Flame Barrier+": 16,
    "Iron Wave": 5,
    "Iron Wave+": 7,
    "True Grit": 7,
    "True Grit+": 9,
    "Power Through": 15,
    "Power Through+": 20,
}
_NONBLOCKING_ACTION_PREFIXES = (
    "End turn", "Use potion", "Play Reckless Charge",
    "Play Bash", "Play Strike", "Play Pommel Strike",
    "Play Cleave", "Play Clothesline", "Play Fire Breathing",
    "Play Dark Embrace", "Play Anger", "Play Uppercut",
    "Play Whirlwind", "Play Heavy Blade", "Play Carnage",
)


def _status_amount(player: dict, target: str) -> int:
    """Read the actual current player power object, never an LLM guess."""
    powers = player.get("powers") or []
    if isinstance(powers, dict):
        powers = list(powers.values())
    for power in powers:
        if not isinstance(power, dict):
            continue
        names = {
            str(power.get(k) or "").strip().casefold()
            for k in ("id", "name", "power_id")
        }
        if target.casefold() in names:
            try:
                return int(power.get("amount", 0) or 0)
            except (TypeError, ValueError):
                return 0
    return 0


def _card_name(action_description: str) -> str | None:
    if not action_description.startswith("Play "):
        return None
    suffix = action_description[5:]
    return re.split(r"\\s+on\\s+", suffix, maxsplit=1, flags=re.IGNORECASE)[0].strip()


def project_simple_block(player: dict, descriptions: list[str]) -> dict:
    """Project known ordinary Block cards using floor per card under Frail.

    The result is a baseline if all listed actions resolve. It is NOT an
    exact simulation and must not be used to assert a guaranteed survival
    outcome when other effects or enemy kills matter.
    """
    frail = _status_amount(player, "Frail") > 0
    dexterity = _status_amount(player, "Dexterity")
    initial_block = max(0, int(player.get("block") or 0))
    known_added = 0
    details = []
    unknown_cards = []
    for action in descriptions:
        card = _card_name(str(action or ""))
        if not card:
            continue
        if card in _STATIC_PRINTED_BLOCK:
            printed = _STATIC_PRINTED_BLOCK[card]
            adjusted = max(0, printed + dexterity)
            effective = math.floor(adjusted * 0.75) if frail else adjusted
            known_added += effective
            details.append({
                "card": card,
                "printed": printed,
                "effective": effective,
            })
        elif not str(action).startswith(_NONBLOCKING_ACTION_PREFIXES):
            unknown_cards.append(card)
    return {
        "frail_active": frail,
        "dexterity_power": dexterity,
        "initial_block": initial_block,
        "known_added_block": known_added,
        "known_projected_block": initial_block + known_added,
        "card_details": details,
        "unmodelled_played_cards": unknown_cards,
        "projection_type": "static_known_card_block_not_full_combat_simulation",
    }


class ContinualC2V131Agent(ParentAgent):
    """v1.3.0 policy and planner with explicit power-aware Block arithmetic."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.completed_run_count < PREVIOUS_COMPLETED_RUN:
            raise ValueError(
                "v1.3.1 requires completed Run 35; found "
                f"{self.completed_run_count} runs."
            )
        self.log_debug(
            f"CONTINUAL_C2_V131_READY: completed={self.completed_run_count}, "
            f"next_run={self.completed_run_count+1}, "
            "block_projection=static_known_cards_frail_dexterity_v1"
        )

    def _block_context(self, game_state, descriptions=None) -> str:
        combat = (game_state or {}).get("combat_state", {}) or {}
        player = combat.get("player", {}) or {}
        projection = project_simple_block(player, descriptions or [])
        frail = projection["frail_active"]
        dex = projection["dexterity_power"]
        lines = [
            "DETERMINISTIC BLOCK-MATH REFERENCE (v1.3.1):",
            "Slay the Spire Frail reduces Block gained from each card by 25%,",
            "rounded DOWN for EACH card separately, after Dexterity is applied.",
            f"Current player Frail={frail}, Dexterity power={dex}, "
            f"existing Block={projection['initial_block']}.",
        ]
        hand = combat.get("hand", []) or []
        seen = set()
        for card in hand:
            if not isinstance(card, dict):
                continue
            name = str(card.get("name") or "")
            if name in seen or name not in _STATIC_PRINTED_BLOCK:
                continue
            seen.add(name)
            printed = _STATIC_PRINTED_BLOCK[name]
            after_dex = max(0, printed + dex)
            effective = math.floor(after_dex * 0.75) if frail else after_dex
            lines.append(f"- {name}: printed={printed}; effective_now={effective}")
        if descriptions:
            lines.extend([
                "KNOWN STATIC BLOCK PROJECTION FOR PROPOSED SEQUENCE:",
                f"known_added={projection['known_added_block']}; "
                f"initial+known={projection['known_projected_block']}",
            ])
            for entry in projection["card_details"]:
                lines.append(
                    f"- {entry['card']}: {entry['printed']} printed -> "
                    f"{entry['effective']} effective"
                )
            if projection["unmodelled_played_cards"]:
                lines.append(
                    "Unmodelled played cards: "
                    + ", ".join(projection["unmodelled_played_cards"])
                )
        lines.extend([
            "Do NOT use printed Block totals when Frail is active.",
            "Do NOT call this projection an exact simulation: dynamic card effects,",
            "enemy deaths, Weak, relic/potion triggers and other modifiers may alter",
            "the real outcome. If unresolved, state the uncertainty and prioritize survival.",
        ])
        return "\n".join(lines)

    def add_memory_to_prompt(
        self,
        decision_type,
        prompt,
        game_state=None,
        memory_category=None,
        output_instruction="Return ONLY the number.",
    ):
        # Preserve v1.3's complete cumulative playbook and exact rule IDs.
        augmented, category, rule_ids = super().add_memory_to_prompt(
            decision_type,
            prompt,
            game_state=game_state,
            memory_category=memory_category,
            output_instruction=output_instruction,
        )
        if category != "COMBAT" or not isinstance(game_state, dict):
            return augmented, category, rule_ids
        # This includes both first-pass combat planning and the verifier.
        proposed = getattr(self, "_v131_proposed_descriptions", None)
        addition = self._block_context(game_state, proposed)
        return augmented + "\n\n" + addition, category, rule_ids

    def _verify_new_combat_plan(self, game_state, actions, selected):
        # v1.3's verifier still owns approve/reject and legal-action validation;
        # enrich it with deterministic arithmetic rather than replacing its
        # strategic decision with a rigid card heuristic.
        proposed = [selected.get("description")] + [
            item.get("description") for item in self._sticky_combat_remaining
        ]
        self._v131_proposed_descriptions = proposed
        try:
            final_selected = super()._verify_new_combat_plan(
                game_state, actions, selected
            )
        finally:
            self._v131_proposed_descriptions = None

        combat = game_state.get("combat_state", {}) or {}
        player = combat.get("player", {}) or {}
        final_descriptions = [final_selected.get("description")] + [
            item.get("description") for item in self._sticky_combat_remaining
        ]
        prior_projection = project_simple_block(player, proposed)
        final_projection = project_simple_block(player, final_descriptions)
        incoming, _ = self._displayed_incoming_damage(game_state)
        static_unblocked = max(0, incoming - final_projection["known_projected_block"])
        self.log_run_event(
            "BLOCK_PROJECTION_V131", game_state,
            proposed=proposed,
            selected=final_descriptions,
            prior_projection=prior_projection,
            final_projection=final_projection,
            displayed_incoming_before_actions=incoming,
            static_unblocked_if_all_attackers_survive=static_unblocked,
            projection_limitation=(
                "Static known cards only; actual incoming damage and block may "
                "change after subsequent actions or unknown effects."
            ),
        )
        if player.get("current_hp") is not None and static_unblocked >= int(player["current_hp"]):
            self.log_debug(
                "BLOCK_PROJECTION_V131_RISK: static projected unblocked damage "
                f"{static_unblocked} versus HP {player['current_hp']}; "
                "evaluate lethal/Weak/potions or other available mitigation."
            )
        return final_selected


# Rebind all inherited entry points; no change to historical v1.3.0 source.
v130.ContinualC2V13Agent = ContinualC2V131Agent
v130.v121.ContinualC2V121Agent = ContinualC2V131Agent
v130.v121.v120.ContinualC2V12Agent = ContinualC2V131Agent
v130.v121.v120.v112.ContinualC2V112Agent = ContinualC2V131Agent
v130.v121.v120.v112.v111.v11.ContinualC2V11Agent = ContinualC2V131Agent
v130.v121.v120.v112.v111.v11.prior.ContinualC2Agent = ContinualC2V131Agent
v130.v121.v120.v112.v111.v11.prior.base.STSAgent = ContinualC2V131Agent


def main():
    v130.main()


if __name__ == "__main__":
    main()
