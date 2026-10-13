from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Any

# ============================================================
# C2 CONTINUAL TEACHING v1.2 — PERSISTENT PLANNING
# ============================================================
#
# Observed failure mode in Runs 29-32:
#   - card rewards were judged one-by-one without a persistent deck plan;
#   - the combat actor produced a whole-turn plan, executed only its first action,
#     then discarded the remainder and could contradict itself on the next call;
#   - every applicable playbook rule was injected into tactical prompts, causing
#     prompt growth as teaching accumulated.
#
# v1.2 begins at Run 33 and changes those three mechanisms while preserving:
#   - all raw C2 memory and authoritative human teaching;
#   - v1.1 expert Ironclad card priors;
#   - the v1.1.2 human-over-prior authority semantics and hard card prohibitions;
#   - seed persistence, Ascension progression, reflection, and safety guards.
#
# Intervention boundary:
#   Runs 16-28: continual-teaching-v1.0
#   Runs 29-32: card-prior + replan-every-action turn planner (v1.1.1)
#   Run 33 onward: persistent deck plan + sticky turn plan + focused memory (v1.2)

CONTROLLER_VERSION = "c2-continual-teaching-v1.2.0-persistent-planning"
INTERVENTION_START_RUN = 33
PREVIOUS_COMPLETED_RUN = 32
DECISION_ARCHITECTURE = "persistent-deck-plan+sticky-turn-plan+focused-memory-v1"

COMBAT_MEMORY_LIMIT = 8
CARD_REWARD_MEMORY_LIMIT = 10
COMBAT_REASONING_EFFORT = "medium"
CARD_REWARD_REASONING_EFFORT = "medium"

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
REFLECTION_DIR = PROJECT_DIR / "reflection"
V112_CONTROLLER = BASE_DIR / "test_connection_c2_continual_v1_1_2.py"
DECK_PLAN_FILE = REFLECTION_DIR / "c2_active_deck_plan.json"

if not V112_CONTROLLER.exists():
    raise FileNotFoundError(f"Missing C2 continual v1.1.2 controller: {V112_CONTROLLER}")

_spec = importlib.util.spec_from_file_location("_c2_continual_v112", V112_CONTROLLER)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Could not load C2 continual v1.1.2 controller.")

v112 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v112)

# Align every inherited metadata layer with the new intervention identity.
v112.CONTROLLER_VERSION = CONTROLLER_VERSION
v112.v111.CONTROLLER_VERSION = CONTROLLER_VERSION
v112.v111.v11.CONTINUAL_CONTROLLER_VERSION = CONTROLLER_VERSION
v112.v111.v11.prior.CONTINUAL_CONTROLLER_VERSION = CONTROLLER_VERSION

base = v112.v111.v11.prior.base
ParentAgent = v112.ContinualC2V112Agent
CARD_PRIORS = v112.v111.v11.CARD_PRIORS
_clean_json_object = v112.v111.v11._clean_json_object


def _source_run_number(rule: dict[str, Any]) -> int:
    latest = 0
    for memory_id in rule.get("source_memory_ids") or []:
        match = re.search(r"(?:^|_)run_(\d+)(?:_|$)", str(memory_id))
        if match:
            latest = max(latest, int(match.group(1)))
    return latest


def _action_signature(description: str) -> str:
    """Normalize a legal-action description across HP changes after attacks."""
    text = str(description or "").strip().lower()
    # Combat attack descriptions include the target's current HP. That value
    # changes after each planned attack, but the semantic action is the same.
    text = re.sub(r"\s*\(\s*\d+\s*hp\s*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class ContinualC2V12Agent(ParentAgent):
    """Run-33+ controller with persistent deck and turn planning."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.completed_run_count < PREVIOUS_COMPLETED_RUN:
            raise ValueError(
                "C2 continual v1.2 must begin only after Run 32 has completed; "
                f"found {self.completed_run_count} completed runs."
            )

        self._sticky_combat_turn = None
        self._sticky_combat_run_id = None
        self._sticky_combat_remaining: list[dict[str, str]] = []
        self._sticky_combat_reason = None

        self.log_debug(
            "CONTINUAL_C2_V12_READY: "
            f"completed_runs={self.completed_run_count}, "
            f"next_run={self.completed_run_count + 1}, "
            f"architecture={DECISION_ARCHITECTURE}"
        )

    def log_run_event(self, event_type, game_state=None, **details):
        completed_before_event = int(getattr(self, "completed_run_count", 0) or 0)
        if completed_before_event >= PREVIOUS_COMPLETED_RUN:
            details["continual_controller_version"] = CONTROLLER_VERSION
            details["decision_architecture"] = DECISION_ARCHITECTURE
            details["intervention_start_run"] = INTERVENTION_START_RUN
        return super().log_run_event(event_type, game_state, **details)

    # --------------------------------------------------------
    # FOCUSED MEMORY RETRIEVAL
    # --------------------------------------------------------

    @staticmethod
    def _memory_rank(rule: dict[str, Any], category: str):
        primary = str(rule.get("category") or "").upper()
        return (
            1 if rule.get("authoritative", False) else 0,
            1 if primary == category else 0,
            1 if primary == "GENERAL" else 0,
            _source_run_number(rule),
            str(rule.get("rule_id") or ""),
        )

    def _focused_memories(self, category: str, limit: int):
        candidates = list(self.retrieve_memories(category))
        candidates.sort(
            key=lambda rule: self._memory_rank(rule, category),
            reverse=True,
        )
        return candidates, candidates[:limit]

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

        limit = COMBAT_MEMORY_LIMIT if category == "COMBAT" else CARD_REWARD_MEMORY_LIMIT
        candidates, memories = self._focused_memories(category, limit)

        rule_ids = [item.get("rule_id") for item in memories]
        source_memory_ids = sorted(
            {
                source_id
                for item in memories
                for source_id in (item.get("source_memory_ids") or [])
            }
        )
        retrieved_categories = [str(item.get("category", "")).upper() for item in memories]
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
            memory_policy="focused_authority_exact_category_recent_v1",
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
focused subset chosen deterministically for this decision so tactical reasoning is
not drowned by the entire accumulated playbook."""

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

    # --------------------------------------------------------
    # PERSISTENT DECK PLAN
    # --------------------------------------------------------

    def _current_run_key(self, game_state) -> str:
        run_id = str(getattr(self, "current_run_id", "") or "").strip()
        if run_id:
            return run_id
        return f"seed:{game_state.get('seed')}"

    def _load_persistent_deck_plan(self, game_state) -> dict[str, Any]:
        if not DECK_PLAN_FILE.exists():
            return {}
        try:
            document = json.loads(DECK_PLAN_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if document.get("run_key") != self._current_run_key(game_state):
            return {}
        plan = document.get("deck_plan")
        return plan if isinstance(plan, dict) else {}

    def _save_persistent_deck_plan(self, game_state, plan: dict[str, Any], **metadata):
        DECK_PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "schema": "c2-persistent-deck-plan-v1",
            "controller_version": CONTROLLER_VERSION,
            "run_key": self._current_run_key(game_state),
            "seed": game_state.get("seed"),
            "act": game_state.get("act"),
            "floor": game_state.get("floor"),
            "deck_plan": plan,
            **metadata,
        }
        DECK_PLAN_FILE.write_text(
            json.dumps(document, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _validate_scores(payload: dict[str, Any], count: int) -> dict[int, float]:
        raw_scores = payload.get("scores")
        if not isinstance(raw_scores, dict):
            raise ValueError("scores must be a JSON object")

        scores: dict[int, float] = {}
        for i in range(count):
            key = str(i)
            if key not in raw_scores:
                raise ValueError(f"scores is missing action {i}")
            value = float(raw_scores[key])
            if value < 0 or value > 100:
                raise ValueError(f"score for action {i} is outside 0-100: {value}")
            scores[i] = value
        return scores

    @staticmethod
    def _argmax_card_score(scores: dict[int, float], actions) -> int:
        best_score = max(scores.values())
        tied = [i for i, value in scores.items() if value == best_score]
        # On an exact tie, prefer Skip because adding a permanent card is the
        # irreversible action and should require positive evidence.
        for i in tied:
            if actions[i].get("command") == "SKIP":
                return i
        return min(tied)

    def choose_card_reward(self, game_state, actions):
        generated_combat_choice = (
            game_state.get("room_phase") == "COMBAT"
            and bool(base.live_monsters(game_state))
        )
        if generated_combat_choice:
            return super().choose_card_reward(game_state, actions)

        # Preserve v1.1.2's deterministic enforcement of unconditional human
        # prohibitions before any expert prior or model score is considered.
        actions = self._filter_human_forbidden_card_rewards(game_state, actions)
        if not actions:
            raise ValueError("Permanent card reward has no legal actions after filtering")

        descriptions = [a["description"] for a in actions]
        prior_lines = self._card_reward_prior_lines(actions)
        previous_plan = self._load_persistent_deck_plan(game_state)

        fallback = 0
        for i, action in enumerate(actions):
            if action.get("command") == "SKIP":
                fallback = i
                break

        prompt = f"""
You are playing Slay the Spire 1 as Ironclad.
This is a PERMANENT deck-building decision.

The main objective is not to collect individually good cards. It is to build a
coherent deck that can win the current Act and continue scaling for later Acts.

PERSISTENT DECK PLAN FROM THE PREVIOUS REWARD
{json.dumps(previous_plan, indent=2, ensure_ascii=False) if previous_plan else 'No plan yet — create the initial plan from the current deck.'}

RUN STATE
HP: {game_state.get('current_hp')}/{game_state.get('max_hp')}
Act: {game_state.get('act')}
Floor: {game_state.get('floor')}
Boss: {game_state.get('act_boss')}
Ascension: {base.ASCENSION}
Keys: {base.format_keys(game_state)}

RELICS
{base.format_relics(game_state)}

CURRENT DECK
{base.format_deck(game_state.get('deck', []))}

EXPERT CARD-QUALITY PRIORS
{prior_lines}

LEGAL ACTIONS
{chr(10).join(f'{i}: {d}' for i, d in enumerate(descriptions))}

STEP 1 — DECK PLAN FIRST
Before judging the offered cards, state the CURRENT deck plan based only on the
cards/relics already owned and the run state. Preserve the previous plan unless
existing deck evidence genuinely requires a pivot. Do NOT invent a new strategy
merely to justify an attractive offered card.

The deck plan must explicitly contain:
- offense: how the deck currently intends to deal enough damage;
- defense: how it intends to prevent/mitigate damage;
- scaling: how it becomes strong enough for bosses/later Acts;
- draw_energy: draw and energy status/needs;
- aoe: AoE status/needs;
- weaknesses: the most important current problems;
- acquisition_priorities: specific functions/cards that would advance the plan;
- avoid: additions that would dilute or conflict with the plan;
- add_policy: OPEN, SELECTIVE, or SKIP_DEFAULT.

STEP 2 — SCORE EVERY OPTION
Score every legal card and Skip/Singing Bowl from 0-100 against that plan.
A card should beat Skip only when adding it has a clear role in the plan or
solves an important immediate survival problem. Generic quality is insufficient.
Consider redundancy, deck dilution, boss matchup, relic synergy, upgrades,
future scaling, and whether the deck already performs that function.

Expert tiers are priors, never commands. Relevant authoritative human teaching
outranks the expert tier.

Return ONLY one JSON object:
{{
  "deck_plan": {{
    "offense": "...",
    "defense": "...",
    "scaling": "...",
    "draw_energy": "...",
    "aoe": "...",
    "weaknesses": ["..."],
    "acquisition_priorities": ["..."],
    "avoid": ["..."],
    "add_policy": "SELECTIVE"
  }},
  "plan_changed": false,
  "plan_change_reason": "why the existing plan changed, or why it stayed stable",
  "scores": {{"0": 0, "1": 0}},
  "reason": "why the highest-scored option best serves the persistent plan"
}}
"""

        if not self.use_llm:
            return actions[fallback]

        augmented_prompt, memory_category, memory_ids = self.add_memory_to_prompt(
            "CARD_REWARD_EVALUATION_V12",
            prompt,
            game_state=game_state,
            memory_category="CARD_REWARD",
            output_instruction=(
                'Return ONLY valid JSON with keys "deck_plan", "plan_changed", '
                '"plan_change_reason", "scores", and "reason".'
            ),
        )
        response, latency_ms = self.call_llm(
            "CARD_REWARD_EVALUATION_V12",
            augmented_prompt,
            game_state=game_state,
            effort=CARD_REWARD_REASONING_EFFORT,
        )
        if response is None:
            raise RuntimeError("call_llm returned None without pausing the experiment")

        answer = response.output_text.strip()
        input_tokens, output_tokens = self.get_usage(response)
        fallback_used = False
        parse_error = None
        payload = None
        deck_plan = previous_plan

        try:
            payload = _clean_json_object(answer)
            scores = self._validate_scores(payload, len(actions))
            selected_index = self._argmax_card_score(scores, actions)
            if isinstance(payload.get("deck_plan"), dict):
                deck_plan = payload["deck_plan"]
        except Exception as exc:
            selected_index = fallback
            scores = {}
            fallback_used = True
            parse_error = f"{type(exc).__name__}: {exc}"

        if deck_plan:
            self._save_persistent_deck_plan(
                game_state,
                deck_plan,
                selected_action=actions[selected_index].get("description"),
                selected_index=selected_index,
                scores={str(k): v for k, v in scores.items()},
                plan_changed=(payload or {}).get("plan_changed"),
                plan_change_reason=(payload or {}).get("plan_change_reason"),
            )

        self.log_debug("")
        self.log_debug("=== CARD_REWARD_EVALUATION_V12 ===")
        self.log_debug(f"GPT answer: {answer}")
        self.log_debug(f"Controller argmax index: {selected_index}")
        self.log_debug(f"Fallback used: {fallback_used}")
        if parse_error:
            self.log_debug(f"Structured parse error: {parse_error}")

        self.log_run_event(
            "LLM_CALL",
            game_state,
            decision_type="CARD_REWARD_EVALUATION_V12",
            legal_actions=descriptions,
            legal_action_count=len(actions),
            raw_answer=answer,
            structured_payload=payload,
            structured_protocol=True,
            controller_selection_mode="argmax_scores_skip_on_tie",
            selected_index=selected_index,
            selected_action=actions[selected_index].get("description"),
            scores={str(k): v for k, v in scores.items()},
            fallback_used=fallback_used,
            parse_error=parse_error,
            reasoning_effort=CARD_REWARD_REASONING_EFFORT,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            base_prompt_characters=len(prompt),
            prompt_characters=len(augmented_prompt),
            memory_category=memory_category,
            memory_ids=memory_ids,
            memory_count=len(memory_ids),
            persistent_deck_plan=deck_plan,
            plan_changed=(payload or {}).get("plan_changed"),
            plan_change_reason=(payload or {}).get("plan_change_reason"),
        )
        return actions[selected_index]

    # --------------------------------------------------------
    # STICKY WHOLE-TURN COMBAT PLANNING
    # --------------------------------------------------------

    def _clear_sticky_plan(self):
        self._sticky_combat_turn = None
        self._sticky_combat_run_id = None
        self._sticky_combat_remaining = []
        self._sticky_combat_reason = None

    def _try_follow_sticky_plan(self, game_state, actions):
        combat = game_state.get("combat_state", {}) or {}
        turn = combat.get("turn")
        run_id = str(getattr(self, "current_run_id", "") or "")

        if not self._sticky_combat_remaining:
            return None
        if self._sticky_combat_turn != turn or self._sticky_combat_run_id != run_id:
            self.log_run_event(
                "STICKY_COMBAT_PLAN_INVALIDATED",
                game_state,
                reason="turn_or_run_changed",
                planned_remaining=self._sticky_combat_remaining,
            )
            self._clear_sticky_plan()
            return None

        expected = self._sticky_combat_remaining[0]
        matches = [
            action
            for action in actions
            if _action_signature(action.get("description")) == expected["signature"]
        ]
        if not matches:
            self.log_run_event(
                "STICKY_COMBAT_PLAN_INVALIDATED",
                game_state,
                reason="next_planned_action_no_longer_legal",
                expected_action=expected,
                legal_actions=[a.get("description") for a in actions],
                planned_remaining=self._sticky_combat_remaining,
            )
            self._clear_sticky_plan()
            return None

        selected = matches[0]
        self._sticky_combat_remaining.pop(0)
        self.log_run_event(
            "STICKY_COMBAT_PLAN_FOLLOWED",
            game_state,
            expected_action=expected.get("description"),
            selected_action=selected.get("description"),
            remaining_plan=self._sticky_combat_remaining,
            original_reason=self._sticky_combat_reason,
        )
        self.log_debug(
            "STICKY_COMBAT_PLAN_FOLLOWED: "
            f"{selected.get('description')} | remaining={len(self._sticky_combat_remaining)}"
        )
        return selected

    def choose_combat(self, game_state, actions):
        sticky = self._try_follow_sticky_plan(game_state, actions)
        if sticky is not None:
            return sticky

        combat = game_state.get("combat_state", {}) or {}
        player = combat.get("player", {}) or {}
        descriptions = [a["description"] for a in actions]

        fallback = 0
        for i, action in enumerate(actions):
            if action.get("kind") == "end":
                fallback = i
                break

        hand_lines = []
        for i, card in enumerate(combat.get("hand", []) or [], start=1):
            hand_lines.append(
                f"{i}: {base.display_card_name(card)} | "
                f"cost={card.get('cost')} | type={card.get('type')} | "
                f"playable={card.get('is_playable')} | "
                f"targeted={card.get('has_target')} | "
                f"exhausts={card.get('exhausts')} | ethereal={card.get('is_ethereal')}"
            )

        monster_lines = []
        for monster_index, monster in base.live_monsters(game_state):
            powers = monster.get("powers", []) or []
            power_summary = ", ".join(
                f"{p.get('name') or p.get('id')}={p.get('amount')}"
                for p in powers
                if isinstance(p, dict)
            ) or "none"
            monster_lines.append(
                f"{monster_index}: {monster.get('name')} | "
                f"HP {monster.get('current_hp')}/{monster.get('max_hp')} | "
                f"Block {monster.get('block')} | Intent {monster.get('intent')} | "
                f"Damage {monster.get('move_adjusted_damage')} x {monster.get('move_hits')} | "
                f"Powers {power_summary}"
            )

        prompt = f"""
You are playing Slay the Spire 1 as Ironclad.
Plan the BEST COMPLETE SEQUENCE using actions that are legal RIGHT NOW.

Unlike the previous controller, the controller will attempt to FOLLOW the rest of
your sequence on subsequent states in this same turn. Therefore action order is a
commitment, not disposable commentary.

TURN
{combat.get('turn')}

PLAYER
HP: {player.get('current_hp')}/{player.get('max_hp')}
Block: {player.get('block')}
Energy: {player.get('energy')}
Full player state: {json.dumps(player, ensure_ascii=False, default=str)}

MONSTERS
{chr(10).join(monster_lines) if monster_lines else 'None'}

HAND
{chr(10).join(hand_lines)}

POTIONS
{base.format_potions(game_state)}

DRAW PILE
{base.format_deck(combat.get('draw_pile', []))}

DISCARD PILE
{base.format_deck(combat.get('discard_pile', []))}

EXHAUST PILE
{base.format_deck(combat.get('exhaust_pile', []))}

LEGAL ACTIONS RIGHT NOW
{chr(10).join(f'{i}: {d}' for i, d in enumerate(descriptions))}

Build action_sequence as indexes into the CURRENT legal-action list above.
Only include actions currently legal. If a draw/random effect may reveal a new
action, stop the committed sequence after that effect; the controller can replan
once the committed sequence is exhausted.

Decision priorities:
1. Check exact/credible lethal first.
2. Estimate incoming damage if enemies survive.
3. If lethal is unavailable, avoid preventable HP loss when available block/Weak
   can materially reduce or fully mitigate damage, unless taking that damage has
   a concrete larger strategic payoff.
4. Order setup before payoff: Strength, Vulnerable, Weak, draw/energy, powers,
   exhaust synergies, then attacks that benefit from them.
5. Do not spend energy on marginal damage if that sacrifices necessary defense
   and does not materially change the fight.
6. Do not waste block when no attack is incoming unless the card has another
   concrete purpose.
7. Preserve valuable potions unless they materially improve survival or the fight.

Return ONLY one JSON object:
{{
  "action_sequence": [0, 2, 5],
  "reason": "why this complete ordering is better than the alternatives"
}}
"""

        if not self.use_llm:
            return actions[fallback]

        augmented_prompt, memory_category, memory_ids = self.add_memory_to_prompt(
            "COMBAT_STICKY_TURN_PLAN_V12",
            prompt,
            game_state=game_state,
            memory_category="COMBAT",
            output_instruction=(
                'Return ONLY valid JSON with keys "action_sequence" and "reason". '
                'Every action_sequence value must be a currently legal action index.'
            ),
        )
        response, latency_ms = self.call_llm(
            "COMBAT_STICKY_TURN_PLAN_V12",
            augmented_prompt,
            game_state=game_state,
            effort=COMBAT_REASONING_EFFORT,
        )
        if response is None:
            raise RuntimeError("call_llm returned None without pausing the experiment")

        answer = response.output_text.strip()
        input_tokens, output_tokens = self.get_usage(response)
        fallback_used = False
        parse_error = None
        payload = None

        try:
            payload = _clean_json_object(answer)
            sequence = payload.get("action_sequence")
            if not isinstance(sequence, list) or not sequence:
                raise ValueError("action_sequence must be a non-empty list")
            indexes = [int(value) for value in sequence]
            if any(index < 0 or index >= len(actions) for index in indexes):
                raise ValueError(f"action_sequence contains out-of-range index: {indexes}")
            selected_index = indexes[0]
        except Exception as exc:
            indexes = [fallback]
            selected_index = fallback
            fallback_used = True
            parse_error = f"{type(exc).__name__}: {exc}"

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
        self._sticky_combat_reason = (payload or {}).get("reason")

        self.log_run_event(
            "STICKY_COMBAT_PLAN_CREATED",
            game_state,
            action_sequence=indexes,
            planned_actions=planned_actions,
            selected_index=selected_index,
            selected_action=actions[selected_index].get("description"),
            remaining_plan=self._sticky_combat_remaining,
            reason=self._sticky_combat_reason,
            fallback_used=fallback_used,
            parse_error=parse_error,
        )

        self.log_debug("")
        self.log_debug("=== COMBAT_STICKY_TURN_PLAN_V12 ===")
        self.log_debug(f"GPT answer: {answer}")
        self.log_debug(f"Selected index: {selected_index}")
        self.log_debug(
            "Sticky remaining: "
            + " -> ".join(item["description"] for item in self._sticky_combat_remaining)
        )
        self.log_debug(f"Fallback used: {fallback_used}")

        self.log_run_event(
            "LLM_CALL",
            game_state,
            decision_type="COMBAT_STICKY_TURN_PLAN_V12",
            legal_actions=descriptions,
            legal_action_count=len(actions),
            raw_answer=answer,
            structured_payload=payload,
            structured_protocol=True,
            selected_index=selected_index,
            fallback_used=fallback_used,
            parse_error=parse_error,
            reasoning_effort=COMBAT_REASONING_EFFORT,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            base_prompt_characters=len(prompt),
            prompt_characters=len(augmented_prompt),
            memory_category=memory_category,
            memory_ids=memory_ids,
            memory_count=len(memory_ids),
            committed_action_sequence=indexes,
            committed_action_descriptions=[item["description"] for item in planned_actions],
        )
        return actions[selected_index]


# Rebind every inherited entry point so the CommunicationMod loop constructs
# this Run-33+ subclass.
v112.ContinualC2V112Agent = ContinualC2V12Agent
v112.v111.v11.ContinualC2V11Agent = ContinualC2V12Agent
v112.v111.v11.prior.ContinualC2Agent = ContinualC2V12Agent
v112.v111.v11.prior.base.STSAgent = ContinualC2V12Agent


def main():
    v112.v111.v11.prior.main()


if __name__ == "__main__":
    main()
