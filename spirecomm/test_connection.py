from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

# ============================================================
# C2 CONTINUAL TEACHING v1.2.1 — APPLICABILITY/RECENCY HOTFIX
# ============================================================
#
# Run 33 exposed a focused-memory ranking bug in v1.2.0. A recent authoritative
# human lesson could correctly declare applies_to=["CARD_REWARD", "COMBAT"] yet
# still be pushed below the COMBAT top-k cutoff because v1.2.0 ranked a rule's
# PRIMARY category ahead of recency.
#
# v1.2.1 keeps the same persistent-deck-plan and sticky-turn architecture. It
# changes only focused-memory ranking/logging:
#   1. retrieve_memories(category) remains the applicability filter;
#   2. authoritative human teaching still outranks non-authoritative rules;
#   3. among applicable authoritative rules, RECENCY outranks primary-category
#      metadata, so a newer cross-category human lesson cannot be hidden merely
#      because its primary category is CARD_REWARD rather than COMBAT;
#   4. primary category is only a tie-breaker after authority and recency.
#
# Intervention history:
#   Runs 16-28: continual-teaching-v1.0
#   Runs 29-32: card-prior + replan-every-action turn planner
#   Run 33: persistent planning v1.2.0
#   Run 34 onward: v1.2.1 applicability/recency retrieval hotfix

CONTROLLER_VERSION = "c2-continual-teaching-v1.2.1-applicability-recency-hotfix"
HOTFIX_START_RUN = 34
DECISION_ARCHITECTURE = "persistent-deck-plan+sticky-turn-plan+focused-memory-v1.1"
MEMORY_POLICY = "focused_authority_applicability_recent_v1"

BASE_DIR = Path(__file__).resolve().parent
V120_CONTROLLER = BASE_DIR / "test_connection_c2_continual_v1_2.py"

if not V120_CONTROLLER.exists():
    raise FileNotFoundError(f"Missing C2 continual v1.2.0 controller: {V120_CONTROLLER}")

_spec = importlib.util.spec_from_file_location("_c2_continual_v120", V120_CONTROLLER)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Could not load C2 continual v1.2.0 controller.")

v120 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v120)

# Keep inherited metadata aligned with the hotfix identity.
v120.CONTROLLER_VERSION = CONTROLLER_VERSION
v120.DECISION_ARCHITECTURE = DECISION_ARCHITECTURE
v120.v112.CONTROLLER_VERSION = CONTROLLER_VERSION
v120.v112.v111.CONTROLLER_VERSION = CONTROLLER_VERSION
v120.v112.v111.v11.CONTINUAL_CONTROLLER_VERSION = CONTROLLER_VERSION
v120.v112.v111.v11.prior.CONTINUAL_CONTROLLER_VERSION = CONTROLLER_VERSION

base = v120.base
ParentAgent = v120.ContinualC2V12Agent


class ContinualC2V121Agent(ParentAgent):
    """v1.2.0 persistent planning with applicability-first recent memory ranking."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.completed_run_count < HOTFIX_START_RUN - 1:
            raise ValueError(
                "C2 continual v1.2.1 must begin only after Run 33 has completed; "
                f"found {self.completed_run_count} completed runs."
            )
        self.log_debug(
            "CONTINUAL_C2_V121_READY: "
            f"completed_runs={self.completed_run_count}, "
            f"next_run={self.completed_run_count + 1}, "
            f"memory_policy={MEMORY_POLICY}"
        )

    @staticmethod
    def _memory_rank(rule: dict[str, Any], category: str):
        """
        retrieve_memories(category) already filters by applicability. Therefore
        primary-category metadata must not outrank a newer applicable human rule.
        """
        primary = str(rule.get("category") or "").upper()
        return (
            1 if rule.get("authoritative", False) else 0,
            v120._source_run_number(rule),
            1 if primary == category else 0,
            1 if primary == "GENERAL" else 0,
            str(rule.get("rule_id") or ""),
        )

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

        if category not in {"COMBAT", "CARD_REWARD"}:
            return super().add_memory_to_prompt(
                decision_type,
                prompt,
                game_state=game_state,
                memory_category=memory_category,
                output_instruction=output_instruction,
            )

        limit = (
            v120.COMBAT_MEMORY_LIMIT
            if category == "COMBAT"
            else v120.CARD_REWARD_MEMORY_LIMIT
        )
        candidates, memories = self._focused_memories(category, limit)

        rule_ids = [item.get("rule_id") for item in memories]
        source_memory_ids = sorted(
            {
                source_id
                for item in memories
                for source_id in (item.get("source_memory_ids") or [])
            }
        )
        retrieved_categories = [
            str(item.get("category", "")).upper() for item in memories
        ]
        authoritative_rule_ids = [
            item.get("rule_id")
            for item in memories
            if item.get("authoritative", False)
        ]

        self.log_run_event(
            "MEMORY_RETRIEVAL",
            game_state,
            decision_type=decision_type,
            memory_category=category,
            memory_policy=MEMORY_POLICY,
            memory_ids=rule_ids,
            source_memory_ids=source_memory_ids,
            retrieved_memory_categories=retrieved_categories,
            authoritative_rule_ids=authoritative_rule_ids,
            authoritative_rule_count=len(authoritative_rule_ids),
            memory_count=len(memories),
            candidate_memory_count=len(candidates),
            omitted_memory_count=max(0, len(candidates) - len(memories)),
            memory_top_k=limit,
            memory_file=str(base.MEMORY_FILE),
            playbook_file=str(base.PLAYBOOK_FILE),
            playbook_updated_through_run=self.playbook.get("updated_through_run"),
        )

        if not memories:
            return prompt, category, rule_ids

        authority = """DECISION AUTHORITY ORDER (highest to lowest):
1. LEGALITY: only currently legal actions may be issued.
2. AUTHORITATIVE HUMAN TEACHING: relevant human teaching is the highest strategic authority.
3. FIXED EXPERT PRIORS: advisory evidence only; never override relevant human teaching.
4. NON-AUTHORITATIVE PLAYBOOK RULES and contextual model reasoning.

The complete raw memory remains stored and auditable. This prompt contains only a
focused subset chosen deterministically from rules whose applies_to scope includes
this decision category. Among applicable authoritative lessons, newer teaching is
preferred before primary-category metadata."""

        augmented_prompt = (
            prompt.rstrip()
            + "\n\n"
            + self.format_memory_block(memories)
            + "\n\n"
            + authority
            + "\n"
            + output_instruction
        )
        return augmented_prompt, category, rule_ids


# Rebind every inherited entry point so the CommunicationMod loop constructs
# the hotfixed Run-34+ subclass.
v120.ContinualC2V12Agent = ContinualC2V121Agent
v120.v112.ContinualC2V112Agent = ContinualC2V121Agent
v120.v112.v111.v11.ContinualC2V11Agent = ContinualC2V121Agent
v120.v112.v111.v11.prior.ContinualC2Agent = ContinualC2V121Agent
v120.v112.v111.v11.prior.base.STSAgent = ContinualC2V121Agent


def main():
    v120.v112.v111.v11.prior.main()


if __name__ == "__main__":
    main()
