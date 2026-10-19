from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

# ================================================================
# C2 CONTINUAL LEARNING — STABLE FEEDBACK CONTROLLER (v1.4.0)
# ================================================================
# Intended for Run 37 onward, AFTER Run 36 has been human-reviewed
# and post-run reflection has updated the playbook through 36.
#
# Design contract:
# - Freeze the gameplay controller and its prompting for longitudinal
#   human-teaching evaluation. Do not tune code after every loss.
# - Preserve ALL applicable historical playbook rules without top-k.
# - Preserve v1.3.1 power-aware Block arithmetic and plan verifier.
# - Keep game-execution safeguards separate from model learning:
#     (a) never carry a sticky action into a different encounter;
#     (b) never blindly execute a queued End turn;
#     (c) when an End turn would take clearly preventable known
#         attack damage, play a legal effective blocking card instead;
#     (d) keep a recoverable log of each controller override.
# - The existing feedback app remains authoritative. The controller
#   waits for review, incorporates it, and only then starts the next
#   run. No code updates are required between runs.
#
# LIMITATIONS: This is an execution safety net, not a complete
# Slay the Spire simulator. Hidden intents, special card interactions,
# conditional relics, energy/cost mutations, and complex lethal
# sequences remain decisions for the LLM. Regression tests cover
# identified invariants; they cannot prove perfect strategic play.
# ================================================================

CONTROLLER_VERSION = "c2-continual-teaching-v1.4.0-stable-feedback-loop"
DECISION_ARCHITECTURE = (
    "cumulative-policy+context-pinning+persistent-deck-plan+"
    "block-aware-verifier+encounter-guard+end-turn-safety-v1"
)
INTERVENTION_START_RUN = 37
PREVIOUS_COMPLETED_RUN = 36
MEMORY_POLICY = "all_applicable_rules_no_topk_with_context_pinning_v1"

BASE_DIR = Path(__file__).resolve().parent
PREVIOUS_CONTROLLER = BASE_DIR / "test_connection_c2_continual_v1_3_1.py"
if not PREVIOUS_CONTROLLER.is_file():
    raise FileNotFoundError(f"Missing preserved v1.3.1 controller: {PREVIOUS_CONTROLLER}")

_spec = importlib.util.spec_from_file_location(
    "_c2_v131_stable_parent", PREVIOUS_CONTROLLER
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Unable to load preserved v1.3.1 controller")
v131 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v131)

# Rebind live event provenance. The original v1.3.1 module/file stays
# untouched and Run 36 remains attributed to its original controller.
v131.CONTROLLER_VERSION = CONTROLLER_VERSION
v131.DECISION_ARCHITECTURE = DECISION_ARCHITECTURE
v131.INTERVENTION_START_RUN = INTERVENTION_START_RUN
v131.v130.CONTROLLER_VERSION = CONTROLLER_VERSION
v131.v130.DECISION_ARCHITECTURE = DECISION_ARCHITECTURE
v131.v130.INTERVENTION_START_RUN = INTERVENTION_START_RUN
v131.v130.v121.CONTROLLER_VERSION = CONTROLLER_VERSION
v131.v130.v121.DECISION_ARCHITECTURE = DECISION_ARCHITECTURE
v131.v130.v121.v120.CONTROLLER_VERSION = CONTROLLER_VERSION
v131.v130.v121.v120.DECISION_ARCHITECTURE = DECISION_ARCHITECTURE
v131.v130.v121.v120.INTERVENTION_START_RUN = INTERVENTION_START_RUN
v131.v130.v121.v120.v112.CONTROLLER_VERSION = CONTROLLER_VERSION
v131.v130.v121.v120.v112.v111.CONTROLLER_VERSION = CONTROLLER_VERSION
v131.v130.v121.v120.v112.v111.v11.CONTINUAL_CONTROLLER_VERSION = CONTROLLER_VERSION
v131.v130.v121.v120.v112.v111.v11.prior.CONTINUAL_CONTROLLER_VERSION = CONTROLLER_VERSION

base = v131.base
ParentAgent = v131.ContinualC2V131Agent

def _active_encounter_key(game_state: dict[str, Any] | None, run_id: str):
    """Encounter identity from stable map coordinates, not combat turn.

    Combat turn 1 repeats on every new encounter. Room transitions also
    invalidate a sticky plan, even if a game's next room is reached while
    a prior turn-1 plan still has a queued End turn.
    """
    if not isinstance(game_state, dict):
        return None
    if str(game_state.get("screen_type") or "").upper() != "NONE":
        return None
    if str(game_state.get("room_phase") or "").upper() != "COMBAT":
        return None
    if not isinstance(game_state.get("combat_state"), dict):
        return None
    if not run_id:
        return None
    act = game_state.get("act")
    floor = game_state.get("floor")
    # No reliable room identity -> be conservative and do not persist.
    if act is None or floor is None:
        return None
    return (
        str(run_id), str(act), str(floor),
        str(game_state.get("room_type") or ""),
    )


def _is_end_turn(action: dict[str, Any] | None) -> bool:
    if not isinstance(action, dict):
        return False
    return (
        str(action.get("kind") or "").lower() == "end"
        or str(action.get("description") or "").strip().lower() == "end turn"
        or str(action.get("command") or "").strip().upper() == "END"
    )


class ContinualC2StableAgent(ParentAgent):
    """One long-lived agent implementation for Run 37 and future feedback."""

    def __init__(self, *args, **kwargs):
        self._stable_encounter_key = None
        super().__init__(*args, **kwargs)

        if self.completed_run_count < PREVIOUS_COMPLETED_RUN:
            raise ValueError(
                "Stable controller starts after Run 36; "
                f"found only {self.completed_run_count} completed runs."
            )
        playbook_run = int(self.playbook.get("updated_through_run") or 0)
        # First adoption must start at a clean Run-36 checkpoint.
        # On LATER runs, however, a crash can occur after RUN_END but
        # before feedback/reflection. The inherited main() deliberately
        # recovers that pending review before starting another run.
        if (
            self.completed_run_count == PREVIOUS_COMPLETED_RUN
            and playbook_run != PREVIOUS_COMPLETED_RUN
        ):
            raise ValueError(
                "Run 36 is not reflected yet. Finish its human review using "
                "test_connection_c2_finalize_run36.py before activating stable mode."
            )
        if (
            self.completed_run_count > PREVIOUS_COMPLETED_RUN
            and playbook_run < self.completed_run_count - 1
        ):
            raise ValueError(
                "More than one completed run is missing reflection; cannot "
                "safely resume automatically. Complete/recover the earlier review."
            )

        # Parent v1.3 validates that every raw teaching is represented in
        # the cumulative playbook. Do NOT truncate any authoritative rule.
        self.log_debug(
            "STABLE_C2_READY: "
            f"completed_runs={self.completed_run_count}, "
            f"next_run={self.completed_run_count + 1}, "
            f"version={CONTROLLER_VERSION}; "
            "controller_locked=true"
        )

    def _clear_sticky_with_audit(self, game_state, reason: str):
        remaining = list(getattr(self, "_sticky_combat_remaining", []) or [])
        if remaining:
            self.log_run_event(
                "STABLE_STICKY_PLAN_INVALIDATED", game_state or {},
                reason=reason,
                discarded_actions=remaining,
            )
        self._clear_sticky_plan()

    def _sync_encounter(self, game_state):
        key = _active_encounter_key(
            game_state, str(getattr(self, "current_run_id", "") or "")
        )
        prior = getattr(self, "_stable_encounter_key", None)
        if key != prior:
            self._clear_sticky_with_audit(game_state, "encounter_or_room_changed")
            self._stable_encounter_key = key
        return key

    def cache_active_state(self, game_state):
        # Base router calls this before every in-game decision. Reward,
        # map, shop, event, and transition screens all clear sticky state.
        self._sync_encounter(game_state)
        return super().cache_active_state(game_state)

    def reset_for_new_run(self):
        self._stable_encounter_key = None
        self._clear_sticky_plan()
        return super().reset_for_new_run()

    def add_memory_to_prompt(
        self, decision_type, prompt, game_state=None,
        memory_category=None, output_instruction="Return ONLY the number.",
    ):
        # Parent owns full cumulative learning and Frail/Dex calculations.
        augmented, category, memory_ids = super().add_memory_to_prompt(
            decision_type, prompt, game_state=game_state,
            memory_category=memory_category,
            output_instruction=output_instruction,
        )
        # These are fixed, universal evaluation instructions, not overrides
        # of historical human teaching or newly learned playbook rules.
        reminders = {
            "COMBAT": (
                "STABLE EXECUTION CHECK: Before ending a turn, inspect current "
                "enemy intent and displayed damage, player HP/Block, effective "
                "status-modified Block, available energy and playable defense. "
                "Compare the immediate survival cost of damage/setup versus "
                "block/Weak/killing a threat. Do not ignore scaling in prolonged "
                "fights when a safe setup opportunity is present."
            ),
            "SHOP": (
                "STABLE SURVIVAL CHECK: Assess HP, upcoming risks and potions "
                "before each purchase; at low HP consider immediate survival "
                "resources before incremental scaling/removal. Recompute after "
                "every purchase; leaving the shop is a valid option."
            ),
            "MAP": (
                "STABLE ROUTE CHECK: Estimate the risk of upcoming enemies/elites "
                "against current HP, potions and deck; take optional elites only "
                "when their expected value justifies the survival risk."
            ),
            "CARD_REWARD": (
                "STABLE DECK CHECK: Skip genuinely weak/off-plan rewards, but "
                "do not skip strong immediate damage, defense or scaling when "
                "the current deck needs it. Do not treat compactness as an "
                "absolute goal."
            ),
        }
        reminder = reminders.get(str(category).upper())
        if reminder:
            augmented = augmented + "\n\n" + reminder
        return augmented, category, memory_ids

    @staticmethod
    def _known_damage_risk(game_state) -> tuple[int, int]:
        combat = (game_state or {}).get("combat_state", {}) or {}
        player = combat.get("player", {}) or {}
        incoming, _ = ContinualC2StableAgent._displayed_incoming_damage(game_state)
        block = max(0, int(player.get("block") or 0))
        return incoming, max(0, incoming - block)

    @staticmethod
    def _best_immediate_block_action(game_state, actions):
        """Choose a legal simple block card only when it reduces known HP loss.

        Uses v1.3.1's effective per-card Frail/Dexterity arithmetic.
        Never invents legal actions. Unknown effects are not assumed.
        """
        combat = (game_state or {}).get("combat_state", {}) or {}
        player = combat.get("player", {}) or {}
        incoming, unblocked = ContinualC2StableAgent._known_damage_risk(game_state)
        if incoming <= 0 or unblocked <= 0:
            return None

        costs: dict[str, int] = {}
        for card in (combat.get("hand") or []):
            if isinstance(card, dict) and card.get("name"):
                try:
                    costs[str(card["name"])] = int(card.get("cost", 1))
                except (TypeError, ValueError):
                    costs[str(card["name"])] = 1

        candidates = []
        for action in actions:
            description = str(action.get("description") or "")
            card = v131._card_name(description)
            if card not in v131._STATIC_PRINTED_BLOCK:
                continue
            projection = v131.project_simple_block(player, [description])
            effective = int(projection["known_added_block"])
            if effective <= 0:
                continue
            # First maximize HP saved. For equal mitigation, prefer a
            # cheaper card so high-impact defensive tools remain available.
            cost = costs.get(card, 1)
            candidates.append((min(unblocked, effective), -cost, -effective, action))
        if not candidates:
            return None
        return max(candidates, key=lambda item: item[:3])[3]

    def _guard_end_turn(self, game_state, actions, selected):
        if not _is_end_turn(selected):
            return selected

        _, unblocked = self._known_damage_risk(game_state)
        safer = self._best_immediate_block_action(game_state, actions)
        if safer is None:
            return selected

        self._clear_sticky_with_audit(game_state, "unsafe_end_turn")
        self.log_run_event(
            "STABLE_END_TURN_GUARD", game_state,
            requested_action=selected.get("description"),
            forced_action=safer.get("description"),
            known_unblocked_damage_before=unblocked,
            safety_reason="preventable_known_attack_damage",
        )
        return safer

    def choose_combat(self, game_state, actions):
        # Normal execution calls cache_active_state first; this second sync
        # protects direct callers, tests, and unusual router state paths.
        key = self._sync_encounter(game_state)

        # No reliable encounter identity: don't reuse sticky continuations.
        if key is None and getattr(self, "_sticky_combat_remaining", None):
            self._clear_sticky_with_audit(game_state, "unidentified_encounter")

        # End turn must be assessed in the REAL current state, not approved
        # earlier in the sequence. Never auto-run a queued End turn.
        remainder = getattr(self, "_sticky_combat_remaining", []) or []
        if remainder and str(remainder[0].get("description") or "").strip().lower() == "end turn":
            self._clear_sticky_with_audit(game_state, "end_turn_requires_new_verification")

        selected = super().choose_combat(game_state, actions)

        # Drop any queued End turn and following actions. Execution can
        # recommence via a fresh verified plan after earlier cards resolve.
        remainder = list(getattr(self, "_sticky_combat_remaining", []) or [])
        end_position = next((
            i for i, item in enumerate(remainder)
            if str(item.get("description") or "").strip().lower() == "end turn"
        ), None)
        if end_position is not None:
            removed = remainder[end_position:]
            self._sticky_combat_remaining = remainder[:end_position]
            self.log_run_event(
                "STABLE_QUEUED_END_TURN_DROPPED", game_state,
                discarded_actions=removed,
            )

        return self._guard_end_turn(game_state, actions, selected)


# The existing CommunicationMod main() dynamically uses the base.STSAgent
# binding. Keep a single stable entrypoint; no more copy-on-every-run.
v131.ContinualC2V131Agent = ContinualC2StableAgent
v131.v130.ContinualC2V13Agent = ContinualC2StableAgent
v131.v130.v121.ContinualC2V121Agent = ContinualC2StableAgent
v131.v130.v121.v120.ContinualC2V12Agent = ContinualC2StableAgent
v131.v130.v121.v120.v112.ContinualC2V112Agent = ContinualC2StableAgent
v131.v130.v121.v120.v112.v111.v11.ContinualC2V11Agent = ContinualC2StableAgent
v131.v130.v121.v120.v112.v111.v11.prior.ContinualC2Agent = ContinualC2StableAgent
v131.v130.v121.v120.v112.v111.v11.prior.base.STSAgent = ContinualC2StableAgent


def main():
    v131.main()


if __name__ == "__main__":
    main()
