from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

# ============================================================
# C2 CONTINUAL TEACHING v1.3 — CUMULATIVE POLICY + VERIFIED PLANNING
# ============================================================
#
# Run 34 showed that top-k focused retrieval is incompatible with the intended
# cumulative-learning experiment. Older authoritative lessons (for example the
# Centurion/Mystic target priority from Run 13) could remain stored permanently
# yet disappear from the actor prompt because newer generic lessons occupied the
# COMBAT/CARD_REWARD cutoff.
#
# v1.3 begins at Run 35 and changes two mechanisms:
#   1. no top-k truncation for learned policy. Every playbook rule whose
#      applies_to scope includes the current decision is included. Startup also
#      verifies that every raw lesson is represented by at least one playbook
#      rule, so cumulative coverage cannot silently shrink.
#   2. newly-created sticky combat plans receive an independent second-pass
#      verification before the first action is returned. The verifier sees the
#      full current hand/monster state, the proposed plan, incoming damage, and
#      the same cumulative policy. It may approve the plan or replace it with a
#      safer/more strategically correct legal sequence.
#
# Context-specific authoritative teachings are never substituted for cumulative
# policy. They are additionally PINNED at the top when current monster/card/relic
# names occur verbatim in the teaching, increasing salience without dropping any
# other applicable rule.
#
# Intervention history:
#   Runs 16-28: continual-teaching-v1.0
#   Runs 29-32: card-prior + replan-every-action planner (actual v1.1.1)
#   Run 33: v1.2.0 persistent planning + top-k focused memory
#   Run 34: v1.2.1 applicability/recency top-k hotfix
#   Run 35+: v1.3 cumulative policy + verified sticky planning

CONTROLLER_VERSION = "c2-continual-teaching-v1.3.0-cumulative-policy-verified-planning"
INTERVENTION_START_RUN = 35
PREVIOUS_COMPLETED_RUN = 34
DECISION_ARCHITECTURE = "cumulative-policy+context-pinning+persistent-deck-plan+verified-sticky-turn-plan-v1"
MEMORY_POLICY = "all_applicable_rules_no_topk_with_context_pinning_v1"
COMBAT_VERIFIER_REASONING_EFFORT = "medium"

BASE_DIR = Path(__file__).resolve().parent
V121_CONTROLLER = BASE_DIR / "test_connection_c2_continual_v1_2_1.py"

if not V121_CONTROLLER.exists():
    raise FileNotFoundError(f"Missing C2 continual v1.2.1 controller: {V121_CONTROLLER}")

_spec = importlib.util.spec_from_file_location("_c2_continual_v121", V121_CONTROLLER)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Could not load C2 continual v1.2.1 controller.")

v121 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v121)

# Align inherited event metadata with the Run-35+ architecture. Historical log
# records are immutable; these globals affect only new events in this process.
v121.CONTROLLER_VERSION = CONTROLLER_VERSION
v121.DECISION_ARCHITECTURE = DECISION_ARCHITECTURE
v121.MEMORY_POLICY = MEMORY_POLICY
v121.v120.CONTROLLER_VERSION = CONTROLLER_VERSION
v121.v120.DECISION_ARCHITECTURE = DECISION_ARCHITECTURE
v121.v120.INTERVENTION_START_RUN = INTERVENTION_START_RUN
v121.v120.v112.CONTROLLER_VERSION = CONTROLLER_VERSION
v121.v120.v112.v111.CONTROLLER_VERSION = CONTROLLER_VERSION
v121.v120.v112.v111.v11.CONTINUAL_CONTROLLER_VERSION = CONTROLLER_VERSION
v121.v120.v112.v111.v11.prior.CONTINUAL_CONTROLLER_VERSION = CONTROLLER_VERSION

base = v121.base
ParentAgent = v121.ContinualC2V121Agent
_clean_json_object = v121.v120._clean_json_object
_action_signature = v121.v120._action_signature
_source_run_number = v121.v120._source_run_number


class ContinualC2V13Agent(ParentAgent):
    """Run-35+ controller with full cumulative policy and verified turn plans."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.completed_run_count < PREVIOUS_COMPLETED_RUN:
            raise ValueError(
                "C2 continual v1.3 must begin only after Run 34 has completed; "
                f"found {self.completed_run_count} completed runs."
            )
        self._validate_cumulative_policy_coverage()
        self.log_debug(
            "CONTINUAL_C2_V13_READY: "
            f"completed_runs={self.completed_run_count}, "
            f"next_run={self.completed_run_count + 1}, "
            f"memory_policy={MEMORY_POLICY}, "
            "combat_verifier=enabled"
        )

    # --------------------------------------------------------
    # CUMULATIVE POLICY INTEGRITY
    # --------------------------------------------------------

    def _all_playbook_rules(self) -> list[dict[str, Any]]:
        return [
            rule
            for rows in (self.playbook.get("categories", {}) or {}).values()
            for rule in (rows or [])
        ]

    def _validate_cumulative_policy_coverage(self) -> None:
        raw_ids = {
            str(item.get("id"))
            for item in self.memory_items
            if item.get("id")
        }
        covered_ids = {
            str(memory_id)
            for rule in self._all_playbook_rules()
            for memory_id in (rule.get("source_memory_ids") or [])
        }
        missing = sorted(raw_ids - covered_ids)
        if missing:
            raise ValueError(
                "v1.3 cumulative-policy coverage failure; raw lessons are not "
                "represented in the playbook: " + ", ".join(missing)
            )

        self.log_run_event(
            "CUMULATIVE_POLICY_COVERAGE_VALIDATED",
            self.last_game_state or {},
            raw_memory_count=len(raw_ids),
            covered_raw_memory_count=len(raw_ids & covered_ids),
            playbook_rule_count=len(self._all_playbook_rules()),
            playbook_updated_through_run=self.playbook.get("updated_through_run"),
            memory_policy=MEMORY_POLICY,
        )

    # --------------------------------------------------------
    # FULL CUMULATIVE MEMORY + CONTEXT PINNING
    # --------------------------------------------------------

    @staticmethod
    def _rule_sort_key(rule: dict[str, Any]):
        # Keep all rules. Ordering is for readability/salience only, never
        # inclusion/exclusion. Authoritative rules are presented first and, within
        # that group, older-to-newer so later corrections remain near the end.
        return (
            0 if rule.get("authoritative", False) else 1,
            _source_run_number(rule),
            str(rule.get("rule_id") or ""),
        )

    @staticmethod
    def _state_entity_names(game_state: dict[str, Any] | None) -> list[str]:
        if not isinstance(game_state, dict):
            return []

        names: list[str] = []

        combat = game_state.get("combat_state", {}) or {}
        for monster in combat.get("monsters", []) or []:
            if isinstance(monster, dict) and monster.get("name"):
                names.append(str(monster["name"]))
        for card in combat.get("hand", []) or []:
            if isinstance(card, dict) and card.get("name"):
                names.append(str(card["name"]))

        for card in game_state.get("deck", []) or []:
            if isinstance(card, dict) and card.get("name"):
                names.append(str(card["name"]))

        screen_state = game_state.get("screen_state", {}) or {}
        for card in screen_state.get("cards", []) or []:
            if isinstance(card, dict) and card.get("name"):
                names.append(str(card["name"]))

        for relic in game_state.get("relics", []) or []:
            if isinstance(relic, dict) and relic.get("name"):
                names.append(str(relic["name"]))

        # Choice lists sometimes expose offered card/event/relic names as strings.
        names.extend(str(x) for x in (game_state.get("choice_list", []) or []))

        ignored = {
            "strike", "strike+", "defend", "defend+", "bash", "bash+",
            "skip", "bowl", "confirm", "return", "cancel",
        }
        result = []
        seen = set()
        for name in names:
            cleaned = " ".join(str(name).strip().split())
            key = cleaned.lower()
            if len(key) < 4 or key in ignored or key in seen:
                continue
            seen.add(key)
            result.append(cleaned)
        return result

    def _pinned_authoritative_rules(
        self,
        memories: list[dict[str, Any]],
        game_state: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        entities = self._state_entity_names(game_state)
        if not entities:
            return []

        pinned = []
        for rule in memories:
            if not rule.get("authoritative", False):
                continue
            text = str(
                rule.get("human_feedback_verbatim")
                or rule.get("guidance")
                or ""
            ).lower()
            matched = [name for name in entities if name.lower() in text]
            if matched:
                copy = dict(rule)
                copy["_matched_entities"] = matched
                pinned.append(copy)
        return pinned

    @staticmethod
    def _format_compact_cumulative_policy(memories: list[dict[str, Any]]) -> str:
        if not memories:
            return "CUMULATIVE LEARNED POLICY: no applicable rules."

        lines = [
            "CUMULATIVE LEARNED POLICY — ALL APPLICABLE RULES:",
            (
                "Nothing below is a recency sample or top-k subset. Every playbook "
                "rule whose applies_to scope includes this decision is present."
            ),
        ]
        for i, rule in enumerate(memories, start=1):
            source_ids = ",".join(str(x) for x in (rule.get("source_memory_ids") or []))
            authority = "AUTHORITATIVE HUMAN" if rule.get("authoritative", False) else "LEARNED"
            lines.append(
                f"{i}. [{authority} | {rule.get('rule_id')} | "
                f"source={source_ids} | category={rule.get('category')}]"
            )
            lines.append(f"   Guidance: {str(rule.get('guidance') or '').strip()}")
            if not rule.get("authoritative", False):
                when = str(rule.get("when") or "").strip()
                if when:
                    lines.append(f"   Apply when: {when}")
        return "\n".join(lines)

    @staticmethod
    def _format_pinned_block(pinned: list[dict[str, Any]]) -> str:
        if not pinned:
            return ""
        lines = [
            "STATE-MATCHED AUTHORITATIVE HUMAN TEACHING — PINNED:",
            (
                "These are repeated from the cumulative policy because the current "
                "state names an enemy/card/relic that appears in the original human teaching."
            ),
        ]
        for rule in pinned:
            lines.append(
                f"- {rule.get('rule_id')} matched={rule.get('_matched_entities', [])}:"
            )
            lines.append(
                "  " + str(
                    rule.get("human_feedback_verbatim")
                    or rule.get("guidance")
                    or ""
                ).strip()
            )
        return "\n".join(lines)

    def add_memory_to_prompt(
        self,
        decision_type,
        prompt,
        game_state=None,
        memory_category=None,
        output_instruction="Return ONLY the number.",
    ):
        category = (
            str(memory_category).upper()
            if memory_category
            else self.default_memory_category(decision_type)
        )

        memories = list(self.retrieve_memories(category))
        memories.sort(key=self._rule_sort_key)
        pinned = self._pinned_authoritative_rules(memories, game_state)

        rule_ids = [item.get("rule_id") for item in memories]
        source_memory_ids = sorted(
            {
                source_id
                for item in memories
                for source_id in (item.get("source_memory_ids") or [])
            }
        )
        authoritative_rule_ids = [
            item.get("rule_id")
            for item in memories
            if item.get("authoritative", False)
        ]
        pinned_rule_ids = [item.get("rule_id") for item in pinned]

        self.log_run_event(
            "MEMORY_RETRIEVAL",
            game_state,
            decision_type=decision_type,
            memory_category=category,
            memory_policy=MEMORY_POLICY,
            memory_ids=rule_ids,
            source_memory_ids=source_memory_ids,
            retrieved_memory_categories=[
                str(item.get("category", "")).upper() for item in memories
            ],
            authoritative_rule_ids=authoritative_rule_ids,
            authoritative_rule_count=len(authoritative_rule_ids),
            pinned_authoritative_rule_ids=pinned_rule_ids,
            pinned_authoritative_rule_count=len(pinned_rule_ids),
            state_entities=self._state_entity_names(game_state),
            memory_count=len(memories),
            candidate_memory_count=len(memories),
            omitted_memory_count=0,
            memory_top_k=None,
            memory_file=str(base.MEMORY_FILE),
            playbook_file=str(base.PLAYBOOK_FILE),
            playbook_updated_through_run=self.playbook.get("updated_through_run"),
        )

        if not memories:
            return prompt, category, rule_ids

        authority = """DECISION AUTHORITY ORDER (highest to lowest):
1. LEGALITY: only currently legal game actions may be issued.
2. AUTHORITATIVE HUMAN TEACHING: relevant human teaching is the highest strategic authority.
3. FIXED EXPERT PRIORS: advisory evidence only; never override relevant human teaching.
4. NON-AUTHORITATIVE PLAYBOOK RULES and contextual model reasoning.

CUMULATIVE-LEARNING REQUIREMENT:
- Newer lessons ADD to the existing policy; they do not replace older lessons.
- Do not ignore an older rule merely because newer generic teaching exists.
- Resolve apparent conflicts using specificity and current-state relevance first;
  use newer teaching as a correction only when it actually contradicts an older rule.
"""

        context_note = ""
        if category == "CARD_REWARD" and isinstance(game_state, dict):
            deck_size = len(game_state.get("deck", []) or [])
            context_note = (
                f"\nCURRENT PERMANENT DECK SIZE: {deck_size}.\n"
                "Treat Skip as a real deck-building action. As the deck grows, a new "
                "card must justify the dilution by filling a named weakness, materially "
                "strengthening the existing plan, or enabling a clear synergy.\n"
            )

        blocks = [prompt.rstrip()]
        if pinned:
            blocks.append(self._format_pinned_block(pinned))
        blocks.append(self._format_compact_cumulative_policy(memories))
        blocks.append(authority + context_note + output_instruction)
        return "\n\n".join(blocks), category, rule_ids

    # --------------------------------------------------------
    # COMBAT PLAN VERIFICATION
    # --------------------------------------------------------

    @staticmethod
    def _displayed_incoming_damage(game_state: dict[str, Any]) -> tuple[int, list[str]]:
        total = 0
        details = []
        for index, monster in base.live_monsters(game_state):
            intent = str(monster.get("intent") or "").upper()
            if "ATTACK" not in intent:
                continue
            damage = int(monster.get("move_adjusted_damage") or 0)
            hits = int(monster.get("move_hits") or 1)
            amount = max(0, damage) * max(1, hits)
            total += amount
            details.append(
                f"{index}:{monster.get('name')} intent={intent} displayed={damage}x{hits}={amount}"
            )
        return total, details

    @staticmethod
    def _selected_action_index(actions, selected) -> int:
        for i, action in enumerate(actions):
            if action is selected:
                return i
        selected_command = selected.get("command")
        selected_description = selected.get("description")
        for i, action in enumerate(actions):
            if (
                action.get("command") == selected_command
                and action.get("description") == selected_description
            ):
                return i
        raise ValueError("Could not map selected combat action back to legal index.")

    def _install_replacement_sticky_plan(
        self,
        game_state: dict[str, Any],
        actions,
        indexes: list[int],
        reason: str,
    ):
        combat = game_state.get("combat_state", {}) or {}
        planned_actions = [
            {
                "description": actions[index].get("description"),
                "signature": _action_signature(actions[index].get("description")),
            }
            for index in indexes
        ]
        self._sticky_combat_turn = combat.get("turn")
        self._sticky_combat_run_id = str(getattr(self, "current_run_id", "") or "")
        self._sticky_combat_remaining = planned_actions[1:]
        self._sticky_combat_reason = reason
        return actions[indexes[0]], planned_actions

    def _verify_new_combat_plan(self, game_state, actions, selected):
        if not self.use_llm:
            return selected

        combat = game_state.get("combat_state", {}) or {}
        player = combat.get("player", {}) or {}
        selected_index = self._selected_action_index(actions, selected)
        proposed_descriptions = [selected.get("description")] + [
            item.get("description") for item in self._sticky_combat_remaining
        ]

        incoming, incoming_details = self._displayed_incoming_damage(game_state)
        current_block = int(player.get("block") or 0)
        displayed_unblocked = max(0, incoming - current_block)

        legal_descriptions = [a.get("description") for a in actions]

        verifier_prompt = f"""
You are the SECOND-PASS combat-plan verifier for an Ironclad Slay the Spire agent.
The first planner has proposed a sticky sequence. Do not rubber-stamp it.
Approve it only if it respects the cumulative human teaching and is tactically sound.

TURN: {combat.get('turn')}
PLAYER HP: {player.get('current_hp')}/{player.get('max_hp')}
CURRENT BLOCK: {current_block}
ENERGY: {player.get('energy')}
DISPLAYED INCOMING ATTACK DAMAGE BEFORE NEW ACTIONS: {incoming}
DISPLAYED UNBLOCKED BEFORE NEW ACTIONS: {displayed_unblocked}
INCOMING DETAILS:
{chr(10).join(incoming_details) if incoming_details else 'No enemy currently has an ATTACK intent.'}

FULL CURRENT HAND JSON
{json.dumps(combat.get('hand', []) or [], ensure_ascii=False, default=str)}

FULL LIVE MONSTER JSON
{json.dumps([m for _, m in base.live_monsters(game_state)], ensure_ascii=False, default=str)}

POTIONS
{base.format_potions(game_state)}

LEGAL ACTIONS RIGHT NOW
{chr(10).join(f'{i}: {d}' for i, d in enumerate(legal_descriptions))}

PROPOSED STICKY SEQUENCE
{chr(10).join(f'{i+1}. {d}' for i, d in enumerate(proposed_descriptions))}

VERIFY ALL OF THE FOLLOWING:
1. Check credible lethal first, including whether killing an attacker removes incoming damage.
2. If lethal is unavailable, calculate whether the proposed sequence takes preventable HP loss.
   If legal Block/Weak/target removal can substantially reduce or fully prevent damage,
   reject a plan that instead spends energy on marginal damage with no larger payoff.
3. Do not waste defensive cards when no attack is incoming unless the card has a concrete
   setup/draw/synergy purpose.
4. Respect encounter-specific authoritative target priorities. If human teaching names
   the current enemies, do not reverse that target priority without a concrete lethal or
   immediate-survival reason.
5. Respect sequencing: setup/debuff (for example Vulnerable) before attacks that benefit.
6. Play to the deck's actual engine and synergies rather than using individually good cards
   in isolation.
7. Preserve scarce/limited defensive resources when ordinary defense is sufficient, but use
   them when ordinary defense is insufficient and HP loss would otherwise be preventable.

If the proposed sequence is good, approve it. If not, return a replacement sequence using
ONLY indexes from the CURRENT legal-action list. Because later actions must still be legal
right now, stop the replacement sequence after a draw/random effect that may change options.

Return ONLY one JSON object:
{{
  "approved": true,
  "replacement_action_sequence": [],
  "estimated_hp_loss": 0,
  "reason": "specific verification reasoning"
}}
"""

        augmented_prompt, memory_category, memory_ids = self.add_memory_to_prompt(
            "COMBAT_PLAN_VERIFIER_V13",
            verifier_prompt,
            game_state=game_state,
            memory_category="COMBAT",
            output_instruction=(
                'Return ONLY valid JSON with keys "approved", '
                '"replacement_action_sequence", "estimated_hp_loss", and "reason".'
            ),
        )

        response, latency_ms = self.call_llm(
            "COMBAT_PLAN_VERIFIER_V13",
            augmented_prompt,
            game_state=game_state,
            effort=COMBAT_VERIFIER_REASONING_EFFORT,
        )
        if response is None:
            raise RuntimeError("combat verifier call_llm returned None without pausing")

        answer = response.output_text.strip()
        input_tokens, output_tokens = self.get_usage(response)
        parse_error = None
        payload = None
        verifier_replaced = False
        final_selected = selected
        final_indexes = None
        final_planned_actions = None

        try:
            payload = _clean_json_object(answer)
            approved = payload.get("approved")
            if not isinstance(approved, bool):
                raise ValueError("approved must be a JSON boolean")

            if approved:
                final_indexes = [selected_index]
            else:
                replacement = payload.get("replacement_action_sequence")
                if not isinstance(replacement, list) or not replacement:
                    raise ValueError(
                        "rejected plan requires non-empty replacement_action_sequence"
                    )
                indexes = [int(value) for value in replacement]
                if any(index < 0 or index >= len(actions) for index in indexes):
                    raise ValueError(
                        f"replacement_action_sequence contains out-of-range index: {indexes}"
                    )
                final_selected, final_planned_actions = self._install_replacement_sticky_plan(
                    game_state,
                    actions,
                    indexes,
                    str(payload.get("reason") or "v1.3 verifier replacement"),
                )
                final_indexes = indexes
                verifier_replaced = True
        except Exception as exc:
            # A verifier-format failure must not silently invent gameplay. Keep the
            # already validated first-pass sticky plan and make the failure auditable.
            parse_error = f"{type(exc).__name__}: {exc}"

        self.log_run_event(
            "COMBAT_PLAN_VERIFICATION_V13",
            game_state,
            proposed_first_index=selected_index,
            proposed_sequence_descriptions=proposed_descriptions,
            displayed_incoming_damage=incoming,
            current_block=current_block,
            displayed_unblocked_damage=displayed_unblocked,
            raw_answer=answer,
            structured_payload=payload,
            verifier_replaced_plan=verifier_replaced,
            final_action_sequence=final_indexes,
            final_planned_actions=final_planned_actions,
            final_selected_action=final_selected.get("description"),
            parse_error=parse_error,
            reasoning_effort=COMBAT_VERIFIER_REASONING_EFFORT,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            memory_category=memory_category,
            memory_ids=memory_ids,
            memory_count=len(memory_ids),
        )

        self.log_debug("")
        self.log_debug("=== COMBAT_PLAN_VERIFICATION_V13 ===")
        self.log_debug(f"Proposed: {' -> '.join(str(x) for x in proposed_descriptions)}")
        self.log_debug(f"Verifier answer: {answer}")
        self.log_debug(f"Verifier replaced plan: {verifier_replaced}")
        if parse_error:
            self.log_debug(f"Verifier parse error: {parse_error}")

        return final_selected

    def choose_combat(self, game_state, actions):
        # Consume an already verified sticky remainder without another LLM call.
        sticky = self._try_follow_sticky_plan(game_state, actions)
        if sticky is not None:
            return sticky

        # Parent v1.2 planner creates a new sticky plan. Because self.add_memory_to_prompt
        # is overridden above, that first pass already receives the full cumulative policy.
        selected = super().choose_combat(game_state, actions)

        # In synthetic test mode the parent does not create an LLM sticky plan.
        if not self.use_llm:
            return selected

        return self._verify_new_combat_plan(game_state, actions, selected)


# Rebind every inherited entry point so CommunicationMod constructs v1.3.
v121.ContinualC2V121Agent = ContinualC2V13Agent
v121.v120.ContinualC2V12Agent = ContinualC2V13Agent
v121.v120.v112.ContinualC2V112Agent = ContinualC2V13Agent
v121.v120.v112.v111.v11.ContinualC2V11Agent = ContinualC2V13Agent
v121.v120.v112.v111.v11.prior.ContinualC2Agent = ContinualC2V13Agent
v121.v120.v112.v111.v11.prior.base.STSAgent = ContinualC2V13Agent


def main():
    v121.main()


if __name__ == "__main__":
    main()
