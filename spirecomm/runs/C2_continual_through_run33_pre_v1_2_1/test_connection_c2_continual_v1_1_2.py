from __future__ import annotations

import importlib.util
import re
from pathlib import Path

# ============================================================
# C2 CONTINUAL TEACHING v1.1.2 — HUMAN AUTHORITY FIX
# ============================================================
#
# v1.1.1 introduced expert Ironclad card priors and whole-turn combat planning.
# A Run-30 observation exposed an integration problem: the actor could still
# rationalize overriding authoritative human teaching when a fixed card prior
# pointed the other way (for example an A-tier prior for a card the human had
# explicitly said not to take).
#
# This wrapper changes only the precedence/instruction-following layer:
#   1. legal game actions remain an absolute constraint;
#   2. AUTHORITATIVE HUMAN TEACHING is the highest STRATEGIC authority;
#   3. expert card priors are advisory and may never override relevant human
#      teaching;
#   4. explicit unconditional human prohibitions such as "do not take Headbutt"
#      are enforced deterministically for permanent card rewards.
#
# Contextual/conditional teaching (for example "do not take X unless Y") is not
# converted into a hard filter; it remains visible to the actor for contextual
# reasoning. This keeps the deterministic layer deliberately narrow.
#
# Intervention boundary:
#   Runs 16-28: continual-teaching-v1.0
#   Run 29-30: v1.1.1 card-prior + turn-planner
#   Run 31 onward: v1.1.2 human-authority enforcement

CONTROLLER_VERSION = "c2-continual-teaching-v1.1.2-human-authority"
HUMAN_AUTHORITY_FIX_START_RUN = 31

BASE_DIR = Path(__file__).resolve().parent
V111_CONTROLLER = BASE_DIR / "test_connection_c2_continual_v1_1_1.py"

if not V111_CONTROLLER.exists():
    raise FileNotFoundError(f"Missing C2 continual v1.1.1 controller: {V111_CONTROLLER}")

_spec = importlib.util.spec_from_file_location("_c2_continual_v111", V111_CONTROLLER)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Could not load C2 continual v1.1.1 controller.")

v111 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v111)

# Keep every metadata layer aligned with this wrapper version.
v111.CONTROLLER_VERSION = CONTROLLER_VERSION
v111.v11.CONTINUAL_CONTROLLER_VERSION = CONTROLLER_VERSION
v111.v11.prior.CONTINUAL_CONTROLLER_VERSION = CONTROLLER_VERSION

base = v111.v11.prior.base
ParentAgent = v111.v11.ContinualC2V11Agent


class ContinualC2V112Agent(ParentAgent):
    """v1.1.1 plus strict human-over-prior authority semantics."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.completed_run_count < HUMAN_AUTHORITY_FIX_START_RUN - 1:
            raise ValueError(
                "C2 continual v1.1.2 must begin only after Run 30 has completed; "
                f"found {self.completed_run_count} completed runs."
            )
        self.log_debug(
            "CONTINUAL_C2_V112_READY: "
            f"completed_runs={self.completed_run_count}, "
            f"next_run={self.completed_run_count + 1}, "
            "authority=legal_actions>authoritative_human_teaching>expert_priors>model"
        )

    # --------------------------------------------------------
    # AUTHORITY PRECEDENCE
    # --------------------------------------------------------

    def add_memory_to_prompt(
        self,
        decision_type,
        prompt,
        game_state=None,
        memory_category=None,
        output_instruction="Return ONLY the number.",
    ):
        augmented_prompt, category, rule_ids = super().add_memory_to_prompt(
            decision_type,
            prompt,
            game_state=game_state,
            memory_category=memory_category,
            output_instruction=output_instruction,
        )

        if not rule_ids:
            return augmented_prompt, category, rule_ids

        old_priority_text = (
            "The CURRENT state and CURRENT legal actions always take priority over learned guidance."
        )
        strict_priority_text = """DECISION AUTHORITY ORDER (highest to lowest):
1. LEGALITY: you may only issue an action that is currently legal in the game.
2. AUTHORITATIVE HUMAN TEACHING: when relevant to this decision, follow it. It is
   the highest strategic authority and must not be overridden by card tiers,
   generic Slay the Spire knowledge, or your own preference.
3. FIXED EXPERT PRIORS: these are advisory evidence only. They help when human
   teaching is silent; they never overrule relevant authoritative human teaching.
4. NON-AUTHORITATIVE PLAYBOOK RULES and your own contextual reasoning.

If authoritative human teaching explicitly says DO NOT / NEVER take, choose,
pick, or add a card and the teaching gives no applicable exception, treat that
as a prohibition. Do not select that card merely because its expert prior is
high or because the current state makes it look attractive.

The current game state determines whether a teaching is relevant and whether an
action is legal; it does NOT grant permission to contradict relevant
AUTHORITATIVE HUMAN TEACHING."""

        if old_priority_text in augmented_prompt:
            augmented_prompt = augmented_prompt.replace(
                old_priority_text,
                strict_priority_text,
                1,
            )
        else:
            # Defensive fallback if the inherited wording changes later.
            augmented_prompt = (
                augmented_prompt.rstrip()
                + "\n\n"
                + strict_priority_text
                + "\n"
                + output_instruction
            )

        return augmented_prompt, category, rule_ids

    # --------------------------------------------------------
    # NARROW DETERMINISTIC HUMAN CARD PROHIBITIONS
    # --------------------------------------------------------

    @staticmethod
    def _split_teaching_sentences(text: str) -> list[str]:
        # Newlines and ordinary sentence punctuation are enough for the short
        # natural-language C2 feedback packets. Preserve apostrophes for don't.
        return [
            piece.strip()
            for piece in re.split(r"[\r\n]+|(?<=[.!?;])\s+", str(text or ""))
            if piece.strip()
        ]

    @classmethod
    def _rule_unconditionally_forbids_card(cls, rule, card_name: str) -> bool:
        if not rule.get("authoritative", False):
            return False

        text = rule.get("human_feedback_verbatim") or rule.get("guidance") or ""
        card = str(card_name or "").strip().lower()
        if not card:
            return False

        directive = re.compile(
            r"\b(?:do\s+not|don't|dont|never|must\s+not|should\s+not)\s+"
            r"(?:ever\s+)?(?:take|pick|choose|add)\b",
            flags=re.IGNORECASE,
        )

        for sentence in cls._split_teaching_sentences(text):
            lowered = sentence.lower()
            if card not in lowered:
                continue
            if not directive.search(sentence):
                continue

            # Conditional statements stay in the LLM reasoning layer rather than
            # being converted into unconditional controller bans.
            if re.search(r"\b(?:unless|except)\b", sentence, flags=re.IGNORECASE):
                continue

            return True

        return False

    def _filter_human_forbidden_card_rewards(self, game_state, actions):
        rules = [
            rule
            for rule in self.retrieve_memories("CARD_REWARD")
            if rule.get("authoritative", False)
        ]

        blocked_indexes = []
        blocked_details = []
        allowed = []

        for original_index, action in enumerate(actions):
            card = action.get("card")
            if not card:
                allowed.append(action)
                continue

            card_name = str(card.get("name") or base.display_card_name(card)).strip()
            matching_rules = [
                rule
                for rule in rules
                if self._rule_unconditionally_forbids_card(rule, card_name)
            ]

            if not matching_rules:
                allowed.append(action)
                continue

            blocked_indexes.append(original_index)
            blocked_details.append(
                {
                    "card": base.display_card_name(card),
                    "original_action_index": original_index,
                    "original_action": action.get("description"),
                    "source_rule_ids": [r.get("rule_id") for r in matching_rules],
                    "source_memory_ids": sorted(
                        {
                            mid
                            for r in matching_rules
                            for mid in (r.get("source_memory_ids") or [])
                        }
                    ),
                }
            )

        # Permanent card rewards should normally retain SKIP/Singing Bowl, but
        # never create an impossible decision if a future game/mod state does not.
        if not allowed:
            self.log_run_event(
                "HUMAN_HARD_CONSTRAINT_NOT_APPLIED",
                game_state,
                reason="filter_would_remove_every_legal_action",
                blocked_details=blocked_details,
            )
            return actions

        if blocked_details:
            self.log_run_event(
                "HUMAN_HARD_CONSTRAINT_APPLIED",
                game_state,
                constraint_type="DO_NOT_TAKE_CARD",
                blocked_original_indexes=blocked_indexes,
                blocked_details=blocked_details,
                original_legal_action_count=len(actions),
                remaining_legal_action_count=len(allowed),
                authority="authoritative_human_teaching",
            )
            self.log_debug(
                "HUMAN_HARD_CONSTRAINT_APPLIED: "
                + ", ".join(item["card"] for item in blocked_details)
            )

        return allowed

    def choose_card_reward(self, game_state, actions):
        # Do not apply permanent deck-building prohibitions to temporary generated
        # card choices during combat/potion resolution.
        generated_combat_choice = (
            game_state.get("room_phase") == "COMBAT"
            and bool(base.live_monsters(game_state))
        )
        if generated_combat_choice:
            return super().choose_card_reward(game_state, actions)

        filtered_actions = self._filter_human_forbidden_card_rewards(
            game_state,
            actions,
        )
        return super().choose_card_reward(game_state, filtered_actions)


# Rebind every inherited entry point so the CommunicationMod loop actually
# constructs the v1.1.2 subclass.
v111.v11.ContinualC2V11Agent = ContinualC2V112Agent
v111.v11.prior.ContinualC2Agent = ContinualC2V112Agent
v111.v11.prior.base.STSAgent = ContinualC2V112Agent


def main():
    v111.v11.prior.main()


if __name__ == "__main__":
    main()
