from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

# ============================================================
# C2 CONTINUAL TEACHING v1.1
# ============================================================
#
# Intervention boundary:
#   Runs 16-28: continual-teaching-v1.0
#   Run 29 onward: this controller
#
# v1.1 changes ONLY two decision mechanisms:
#   1. permanent Ironclad card rewards use fixed expert card-quality priors and
#      explicitly score Skip/Singing Bowl alongside every offered card;
#   2. combat decisions first form a whole-turn plan, then execute only the
#      first currently legal action. The next state is always re-planned.
#
# All v1.0 C2 memory, authoritative human teaching, run management, safety
# guards, random seed persistence, and Ascension progression remain unchanged.

CONTINUAL_CONTROLLER_VERSION = "c2-continual-teaching-v1.1-card-prior-turn-planner"
INTERVENTION_START_RUN = 29
PREVIOUS_CHECKPOINT_RUN = 28
CARD_PRIOR_SCHEMA = "ironclad-card-priors-v1"
COMBAT_REASONING_EFFORT = "medium"
CARD_REWARD_REASONING_EFFORT = "medium"

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
REFLECTION_DIR = PROJECT_DIR / "reflection"

V10_CONTROLLER = BASE_DIR / "test_connection_c2_continual_v1.py"
CARD_PRIOR_FILE = REFLECTION_DIR / "ironclad_card_priors.json"

if not V10_CONTROLLER.exists():
    raise FileNotFoundError(f"Missing continual C2 v1.0 controller: {V10_CONTROLLER}")
if not CARD_PRIOR_FILE.exists():
    raise FileNotFoundError(f"Missing Ironclad card-prior file: {CARD_PRIOR_FILE}")

_spec = importlib.util.spec_from_file_location("_c2_continual_v10", V10_CONTROLLER)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Could not load continual C2 v1.0 controller.")

prior = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prior)

# Make the inherited run-event metadata use the new controller identity.
prior.CONTINUAL_CONTROLLER_VERSION = CONTINUAL_CONTROLLER_VERSION
base = prior.base

_card_prior_document = json.loads(CARD_PRIOR_FILE.read_text(encoding="utf-8"))
if _card_prior_document.get("schema") != CARD_PRIOR_SCHEMA:
    raise ValueError(
        f"Expected {CARD_PRIOR_SCHEMA} in {CARD_PRIOR_FILE}, "
        f"got {_card_prior_document.get('schema')!r}."
    )
CARD_PRIORS = _card_prior_document.get("cards", {}) or {}


def _clean_json_object(text: str) -> dict[str, Any]:
    """Parse a single JSON object, tolerating accidental Markdown fences."""
    cleaned = str(text or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(cleaned[start : end + 1])

    if not isinstance(value, dict):
        raise ValueError("Structured decision response must be a JSON object.")
    return value


class ContinualC2V11Agent(prior.ContinualC2Agent):
    """Continual C2 with card-acquisition priors and turn-level combat planning."""

    # --------------------------------------------------------
    # VERSION / INTERVENTION METADATA
    # --------------------------------------------------------

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.completed_run_count < PREVIOUS_CHECKPOINT_RUN:
            raise ValueError(
                "C2 continual v1.1 must start from the completed Run-28 "
                f"checkpoint; found only {self.completed_run_count} completed runs."
            )
        self.log_debug(
            "CONTINUAL_C2_V11_READY: "
            f"completed_runs={self.completed_run_count}, "
            f"next_run={self.completed_run_count + 1}, "
            f"card_priors={len(CARD_PRIORS)}, "
            f"ascension={base.ASCENSION}."
        )

    def log_run_event(self, event_type, game_state=None, **details):
        completed_before_event = int(getattr(self, "completed_run_count", 0) or 0)
        if completed_before_event >= PREVIOUS_CHECKPOINT_RUN:
            details["continual_controller_version"] = CONTINUAL_CONTROLLER_VERSION
            details.setdefault("decision_architecture", "card-prior+turn-planner-v1")
            details.setdefault("intervention_start_run", INTERVENTION_START_RUN)
        return super().log_run_event(event_type, game_state, **details)

    # --------------------------------------------------------
    # SHARED STRUCTURED DECISION HELPER
    # --------------------------------------------------------

    def _structured_choice(
        self,
        *,
        label,
        prompt,
        actions,
        game_state,
        fallback,
        memory_category,
        effort,
        choice_field,
        output_instruction,
    ):
        if not actions:
            raise ValueError(f"{label} received no legal actions")

        fallback = min(max(int(fallback), 0), len(actions) - 1)
        legal_actions = [a["description"] for a in actions]

        if not self.use_llm:
            self.log_run_event(
                "LLM_CALL_SKIPPED_TEST_MODE",
                game_state,
                decision_type=label,
                legal_actions=legal_actions,
                selected_index=fallback,
                structured_protocol=True,
            )
            return actions[fallback]

        augmented_prompt, resolved_memory_category, memory_ids = self.add_memory_to_prompt(
            label,
            prompt,
            game_state=game_state,
            memory_category=memory_category,
            output_instruction=output_instruction,
        )

        response, latency_ms = self.call_llm(
            label,
            augmented_prompt,
            game_state=game_state,
            effort=effort,
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
            index = int(payload[choice_field])
            if not 0 <= index < len(actions):
                raise ValueError(f"{choice_field} out of range: {index}")
        except Exception as exc:
            index = fallback
            fallback_used = True
            parse_error = f"{type(exc).__name__}: {exc}"

        self.log_debug("")
        self.log_debug(f"=== {label} ===")
        self.log_debug(f"GPT answer: {answer}")
        self.log_debug(f"Selected index: {index}")
        self.log_debug(f"Fallback used: {fallback_used}")
        if parse_error:
            self.log_debug(f"Structured parse error: {parse_error}")
        self.log_debug(f"Latency ms: {latency_ms}")
        self.log_debug(f"Input tokens: {input_tokens}")
        self.log_debug(f"Output tokens: {output_tokens}")

        self.log_run_event(
            "LLM_CALL",
            game_state,
            decision_type=label,
            legal_actions=legal_actions,
            legal_action_count=len(actions),
            raw_answer=answer,
            structured_payload=payload,
            structured_protocol=True,
            choice_field=choice_field,
            selected_index=index,
            fallback_used=fallback_used,
            parse_error=parse_error,
            reasoning_effort=effort,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            base_prompt_characters=len(prompt),
            prompt_characters=len(augmented_prompt),
            memory_category=resolved_memory_category,
            memory_ids=memory_ids,
            memory_count=len(memory_ids),
        )
        return actions[index]

    # --------------------------------------------------------
    # EXPERT CARD PRIOR
    # --------------------------------------------------------

    @staticmethod
    def _card_prior(card_name: str) -> dict[str, Any] | None:
        entry = CARD_PRIORS.get(str(card_name or "").strip())
        if not entry:
            return None
        result = dict(entry)
        if str(card_name).strip() == "Clash":
            if int(base.ASCENSION) >= 10:
                result["tier"] = "D"
                result["score"] = 1.5
            else:
                result["tier"] = "B"
                result["score"] = 3.5
        return result

    def _card_reward_prior_lines(self, actions):
        lines = []
        for i, action in enumerate(actions):
            card = action.get("card")
            if card:
                name = str(card.get("name") or base.display_card_name(card))
                prior_entry = self._card_prior(name)
                if prior_entry:
                    lines.append(
                        f"{i}: {base.display_card_name(card)} | "
                        f"expert prior={prior_entry.get('tier')} "
                        f"({prior_entry.get('score')}/5)"
                    )
                else:
                    lines.append(
                        f"{i}: {base.display_card_name(card)} | expert prior=UNRATED"
                    )
            elif action.get("command") == "SKIP":
                lines.append(f"{i}: Skip | no fixed tier; evaluate deck dilution explicitly")
            elif str(action.get("choice", "")).lower() == "bowl":
                lines.append(f"{i}: Singing Bowl | no fixed tier; compare +2 Max HP explicitly")
            else:
                lines.append(f"{i}: {action.get('description')} | no fixed tier")
        return "\n".join(lines)

    def choose_card_reward(self, game_state, actions):
        # Generated cards from combat/potions are temporary tactical choices,
        # so deck-building tiers do not apply. Preserve v1.0 behavior there.
        generated_combat_choice = (
            game_state.get("room_phase") == "COMBAT"
            and bool(base.live_monsters(game_state))
        )
        if generated_combat_choice:
            return super().choose_card_reward(game_state, actions)

        descriptions = [a["description"] for a in actions]
        prior_lines = self._card_reward_prior_lines(actions)

        fallback = 0
        for i, action in enumerate(actions):
            if action.get("command") == "SKIP":
                fallback = i
                break

        prompt = f"""
You are playing Slay the Spire 1 as Ironclad.
Evaluate this PERMANENT card reward as a deck-building decision.

Your job is NOT to take the highest-tier card automatically.
The expert tier is only a general prior. Context can override it.

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

Evaluate EVERY legal option, including Skip or Singing Bowl when present.
For each option assign a contextual value from 0 to 100.

When scoring, explicitly consider:
- whether the deck actually needs this card's function;
- deck size and the cost of dilution;
- existing copies and redundancy;
- damage, block, draw, energy, AoE and scaling needs;
- relic/card synergies and anti-synergies;
- current Act, upcoming boss and expected elites;
- whether Skip is better than adding a mediocre or redundant card.

A high expert tier is evidence, not an instruction.
A low-tier card can still be correct when it solves an immediate deck weakness.
Skipping a card is often correct once the deck no longer needs generic additions.

Return one JSON object only:
{{
  "scores": {{"0": 0, "1": 0}},
  "choice": 0,
  "reason": "brief explanation of why this option beats the alternatives"
}}
"""
        return self._structured_choice(
            label="CARD_REWARD_EVALUATION_V11",
            prompt=prompt,
            actions=actions,
            game_state=game_state,
            fallback=fallback,
            memory_category="CARD_REWARD",
            effort=CARD_REWARD_REASONING_EFFORT,
            choice_field="choice",
            output_instruction=(
                'Return ONLY valid JSON with keys "scores", "choice", and "reason". '
                '"choice" must be one legal action index.'
            ),
        )

    # --------------------------------------------------------
    # WHOLE-TURN COMBAT PLANNING
    # --------------------------------------------------------

    def choose_combat(self, game_state, actions):
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
Do NOT choose the next card greedily in isolation.

First plan the BEST REMAINDER OF THE CURRENT TURN.
Then choose only the FIRST legal action of that plan.
The controller will refresh the state and ask you to plan again after every action,
so do not assume later steps will be executed blindly.

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

Before choosing the first action:
1. Check whether lethal is possible this turn and on which target(s).
2. Estimate incoming damage if enemies survive.
3. Build an ordered turn sequence using the current energy, draw and potions.
4. Consider setup-before-payoff ordering: draw/energy generation, Strength,
   Vulnerable/Weak, powers, exhaust synergies and multi-hit scaling when relevant.
5. Compare offense with the HP cost of insufficient block.
6. Do not END while a remaining action has clear positive value, but do not play
   cards or potions merely because they are available.
7. Preserve valuable potions when they do not materially improve this fight.

The turn_plan is advisory and should describe the intended order from the current
state. first_action MUST be one of the currently legal indexes above.

Return one JSON object only:
{{
  "first_action": 0,
  "turn_plan": [
    "first intended action",
    "second intended action",
    "eventual End Turn"
  ],
  "reason": "brief explanation of the ordering and defensive/offensive objective"
}}
"""
        return self._structured_choice(
            label="COMBAT_TURN_PLAN_V11",
            prompt=prompt,
            actions=actions,
            game_state=game_state,
            fallback=fallback,
            memory_category="COMBAT",
            effort=COMBAT_REASONING_EFFORT,
            choice_field="first_action",
            output_instruction=(
                'Return ONLY valid JSON with keys "first_action", "turn_plan", and "reason". '
                '"first_action" must be one legal action index.'
            ),
        )


# Reuse the thoroughly tested v1.0 CommunicationMod stdin/stdout loop, but make
# it instantiate this subclass instead of the v1.0 agent.
prior.ContinualC2Agent = ContinualC2V11Agent


if __name__ == "__main__":
    prior.main()
