import json
import queue
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

AGENT_VERSION = "baseline-v1.0.2"
EXPERIMENT_TAG = "baseline_v1_30_runs_resilience_patch"
MODEL = "gpt-5.6-luna"
CHARACTER = "IRONCLAD"
ASCENSION = 0
MAX_COMPLETED_RUNS = 30

# LLM request robustness. A transient API/network failure must never leave
# CommunicationMod waiting forever for a command. We retry a few times and,
# if all attempts fail, use the decision branch's existing safe fallback.
LLM_REQUEST_TIMEOUT_SECONDS = 90.0
LLM_MAX_ATTEMPTS = 3
LLM_RETRY_DELAY_SECONDS = 2.0

# Protocol resilience. CommunicationMod should send a new state after every
# command. If that reply is lost, request STATE so an unattended run cannot
# sit forever waiting on stdin.
STATE_RESPONSE_TIMEOUT_SECONDS = 30.0
WATCHDOG_STATE_REQUEST_LIMIT = 10
WATCHDOG_RETRY_DELAY_SECONDS = 30.0

BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "sts_messages.log"
DEBUG_FILE = BASE_DIR / "agent_debug.log"
EVENTS_FILE = BASE_DIR / "run_events.jsonl"
STATE_DUMPS_FILE = BASE_DIR / "state_dumps.jsonl"

# Small pacing delay so the controller does not hammer the Java game loop.
# 0.15 s is intentionally tiny relative to LLM latency but helps reduce sustained CPU load.
COMMAND_DELAY_SECONDS = 0.15

# Routine state logging is compact and rate-limited. Full JSON is only dumped
# for unhandled/error states.
STATE_SUMMARY_MIN_INTERVAL_SECONDS = 2.0


# ============================================================
# SMALL HELPERS
# ============================================================

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def create_run_id():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def display_card_name(card):
    name = card.get("name", "Unknown")
    upgrades = card.get("upgrades", 0) or 0
    if upgrades > 0 and "+" not in name:
        name += f"+{upgrades}"
    return name


def format_card(card):
    return (
        f"{display_card_name(card)} "
        f"(type={card.get('type')}, cost={card.get('cost')}, "
        f"rarity={card.get('rarity')})"
    )


def format_deck(deck):
    if not deck:
        return "None"
    return "\n".join(f"{i}: {format_card(card)}" for i, card in enumerate(deck))


def format_relics(game_state):
    relics = game_state.get("relics", []) or []
    if not relics:
        return "None"
    return ", ".join(
        f"{r.get('name')} (counter={r.get('counter')})" for r in relics
    )


def format_potions(game_state):
    potions = game_state.get("potions", []) or []
    lines = []
    for i, potion in enumerate(potions):
        if potion.get("id") == "Potion Slot":
            lines.append(f"slot {i}: EMPTY")
        else:
            lines.append(
                f"slot {i}: {potion.get('name')} "
                f"(can_use={potion.get('can_use')}, "
                f"can_discard={potion.get('can_discard')}, "
                f"requires_target={potion.get('requires_target')})"
            )
    return "\n".join(lines) if lines else "None"


def format_keys(game_state):
    keys = game_state.get("keys", {}) or {}
    return (
        f"ruby={keys.get('ruby', False)}, "
        f"emerald={keys.get('emerald', False)}, "
        f"sapphire={keys.get('sapphire', False)}"
    )


def live_monsters(game_state):
    combat = game_state.get("combat_state", {}) or {}
    result = []
    for i, monster in enumerate(combat.get("monsters", []) or []):
        if monster.get("is_gone", False) or monster.get("half_dead", False):
            continue
        result.append((i, monster))
    return result


def format_monsters(game_state):
    monsters = live_monsters(game_state)
    if not monsters:
        return "None"
    lines = []
    for i, monster in monsters:
        lines.append(
            f"{i}: {monster.get('name')} | "
            f"HP {monster.get('current_hp')}/{monster.get('max_hp')} | "
            f"Block {monster.get('block')} | "
            f"Intent {monster.get('intent')} | "
            f"Damage {monster.get('move_adjusted_damage')} x {monster.get('move_hits')}"
        )
    return "\n".join(lines)


def has_empty_potion_slot(game_state):
    return any(
        potion.get("id") == "Potion Slot"
        for potion in (game_state.get("potions", []) or [])
    )


def actual_potions(game_state):
    return [
        (i, potion)
        for i, potion in enumerate(game_state.get("potions", []) or [])
        if potion.get("id") != "Potion Slot"
    ]


def lower_list(items):
    return [str(item).lower() for item in (items or [])]


# ============================================================
# AGENT
# ============================================================

class STSAgent:
    """
    CommunicationMod controller + LLM decision layer.

    use_llm=False is used by the synthetic router tests. In that mode,
    decisions use the supplied fallback index and never call OpenAI.
    """

    def __init__(self, use_llm=True, enable_logging=True):
        self.use_llm = use_llm
        self.enable_logging = enable_logging
        if use_llm:
            from openai import OpenAI
            # Disable SDK-level retries so retries are visible in our own logs.
            self.client = OpenAI(
                timeout=LLM_REQUEST_TIMEOUT_SECONDS,
                max_retries=0,
            )
        else:
            self.client = None

        self.current_run_id = None
        self.was_in_game = False
        self.start_command_sent = False
        self.run_end_logged = False

        # Baseline batch control. Count completed RUN_END events already present
        # in this experiment log so the 30-run batch can safely resume after a
        # script/game restart without starting the count over from zero.
        self.completed_run_count = self.load_completed_run_count()
        self.experiment_complete = self.completed_run_count >= MAX_COMPLETED_RUNS

        self.entered_shop_rooms = set()
        self.pending_grid_context = None
        self.last_screen_type = None

        self.last_game_state = None
        self.last_combat_game_state = None
        self.last_state_log_signature = None
        self.last_state_log_time = 0.0

        # Some installed CommunicationMod versions do not expose the documented
        # game_state["keys"] object. Keep a controller-side mirror so prompts and
        # experiment logs still know which Act 4 keys have been acquired.
        self.tracked_keys = {"ruby": False, "emerald": False, "sapphire": False}
        self.pending_key_acquisition = None

        # GRID no-progress guard. Some special GRID interactions (notably
        # Match and Keep / partially-observed selection screens) can return an
        # unchanged state after CHOOSE. Remember the last choice for an
        # identical GRID state so we do not select the same item forever.
        self.last_grid_fingerprint = None
        self.last_grid_command = None

    # --------------------------------------------------------
    # LOGGING
    # --------------------------------------------------------

    def log_debug(self, message=""):
        if not self.enable_logging:
            return
        with open(DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(str(message) + "\n")

    def load_completed_run_count(self):
        """Count completed runs already logged for this exact experiment."""
        if not EVENTS_FILE.exists():
            return 0

        count = 0
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if (
                        event.get("event_type") == "RUN_END"
                        and event.get("agent_version") == AGENT_VERSION
                        and event.get("experiment_tag") == EXPERIMENT_TAG
                    ):
                        count += 1
        except Exception as exc:
            self.log_debug(
                f"RUN_COUNT_LOAD_ERROR: {type(exc).__name__}: {exc}"
            )
            return 0

        return count

    def compact_state_summary(self, state):
        game_state = state.get("game_state", {}) or {}
        combat = game_state.get("combat_state", {}) or {}
        player = combat.get("player", {}) or {}

        monsters = []
        for monster in combat.get("monsters", []) or []:
            if monster.get("is_gone", False):
                continue
            monsters.append(
                {
                    "name": monster.get("name"),
                    "hp": monster.get("current_hp"),
                    "max_hp": monster.get("max_hp"),
                    "block": monster.get("block"),
                    "intent": monster.get("intent"),
                }
            )

        hand = [display_card_name(c) for c in (combat.get("hand", []) or [])]

        return {
            "timestamp": utc_now_iso(),
            "ready_for_command": state.get("ready_for_command"),
            "in_game": state.get("in_game"),
            "available_commands": state.get("available_commands", []),
            "seed": game_state.get("seed"),
            "act": game_state.get("act"),
            "floor": game_state.get("floor"),
            "screen_type": game_state.get("screen_type"),
            "screen_name": game_state.get("screen_name"),
            "room_type": game_state.get("room_type"),
            "room_phase": game_state.get("room_phase"),
            "hp": game_state.get("current_hp"),
            "max_hp": game_state.get("max_hp"),
            "gold": game_state.get("gold"),
            "choices": game_state.get("choice_list", []),
            "combat": {
                "turn": combat.get("turn"),
                "energy": player.get("energy"),
                "block": player.get("block"),
                "hand": hand,
                "monsters": monsters,
            } if combat else None,
        }

    def log_state_summary(self, state):
        if not self.enable_logging:
            return

        game_state = state.get("game_state", {}) or {}
        combat = game_state.get("combat_state", {}) or {}
        signature = (
            bool(state.get("in_game", False)),
            game_state.get("floor"),
            game_state.get("screen_type"),
            game_state.get("room_phase"),
            game_state.get("room_type"),
            combat.get("turn"),
        )

        now = time.monotonic()
        if (
            signature == self.last_state_log_signature
            and now - self.last_state_log_time < STATE_SUMMARY_MIN_INTERVAL_SECONDS
        ):
            return

        self.last_state_log_signature = signature
        self.last_state_log_time = now

        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(self.compact_state_summary(state), ensure_ascii=False) + "\n")
        except Exception as exc:
            self.log_debug(f"STATE_SUMMARY_LOG_ERROR: {type(exc).__name__}: {exc}")

    def dump_full_state(self, reason, state):
        """Write a complete state only when something unusual needs diagnosis."""
        if not self.enable_logging:
            return
        try:
            payload = {
                "timestamp": utc_now_iso(),
                "run_id": self.current_run_id,
                "agent_version": AGENT_VERSION,
                "reason": reason,
                "state": state,
            }
            with open(STATE_DUMPS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception as exc:
            self.log_debug(f"STATE_DUMP_ERROR: {type(exc).__name__}: {exc}")

    def log_run_event(self, event_type, game_state=None, **details):
        if not self.enable_logging:
            return

        try:
            event = {
                "timestamp": utc_now_iso(),
                "run_id": self.current_run_id,
                "agent_version": AGENT_VERSION,
                "model": MODEL,
                "experiment_tag": EXPERIMENT_TAG,
                "event_type": event_type,
            }

            if game_state:
                event.update(
                    {
                        "seed": game_state.get("seed"),
                        "act": game_state.get("act"),
                        "floor": game_state.get("floor"),
                        "screen_type": game_state.get("screen_type"),
                        "screen_name": game_state.get("screen_name"),
                        "room_phase": game_state.get("room_phase"),
                        "room_type": game_state.get("room_type"),
                        "current_hp": game_state.get("current_hp"),
                        "max_hp": game_state.get("max_hp"),
                        "gold": game_state.get("gold"),
                        "act_boss": game_state.get("act_boss"),
                        "keys": self.get_effective_keys(game_state),
                    }
                )

            event.update(details)

            with open(EVENTS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")

        except Exception as exc:
            self.log_debug(f"EVENT_LOG_ERROR: {type(exc).__name__}: {exc}")

    def get_effective_keys(self, game_state=None):
        """Return key ownership even when CommunicationMod omits game_state['keys']."""
        result = dict(self.tracked_keys)
        state_keys = (game_state or {}).get("keys")
        if isinstance(state_keys, dict):
            for key in ("ruby", "emerald", "sapphire"):
                if key in state_keys:
                    result[key] = bool(state_keys[key])
        return result

    def sync_keys_from_state(self, game_state):
        """Use CommunicationMod's key object when the installed version provides it."""
        state_keys = (game_state or {}).get("keys")
        if not isinstance(state_keys, dict):
            return
        for key in ("ruby", "emerald", "sapphire"):
            if key in state_keys:
                self.tracked_keys[key] = bool(state_keys[key])

    def infer_pending_key_from_action(self, decision_type, selected_action, command):
        """Remember a key-producing action; commit it when the next in-game state arrives."""
        selected = str(selected_action or "").lower()
        command_lower = str(command or "").lower()

        if decision_type == "SAPPHIRE_KEY_DECISION" and selected.startswith("take the sapphire key"):
            self.pending_key_acquisition = "sapphire"
        elif decision_type == "REWARD_SAPPHIRE_KEY":
            self.pending_key_acquisition = "sapphire"
        elif decision_type == "REST_DECISION" and (selected.startswith("recall:") or command_lower == "choose recall"):
            self.pending_key_acquisition = "ruby"
        elif decision_type == "REWARD_KEY":
            if "emerald" in selected or "emerald" in command_lower:
                self.pending_key_acquisition = "emerald"
            elif "ruby" in selected or "ruby" in command_lower:
                self.pending_key_acquisition = "ruby"
            elif "sapphire" in selected or "sapphire" in command_lower:
                self.pending_key_acquisition = "sapphire"

    def action(
        self,
        command,
        game_state,
        decision_type,
        decision_source,
        legal_actions=None,
        selected_action=None,
        metadata=None,
    ):
        self.infer_pending_key_from_action(decision_type, selected_action, command)
        self.log_run_event(
            "ACTION",
            game_state,
            decision_type=decision_type,
            decision_source=decision_source,
            legal_actions=legal_actions,
            selected_action=selected_action,
            command=command,
            status="issued",
            metadata=metadata or {},
        )
        return command

    # --------------------------------------------------------
    # LLM
    # --------------------------------------------------------

    @staticmethod
    def get_usage(response):
        try:
            return response.usage.input_tokens, response.usage.output_tokens
        except Exception:
            return None, None

    def call_llm(self, label, prompt, game_state=None, effort="low"):
        """
        Call the LLM with bounded retries.

        CommunicationMod sends a state and then waits for a command. If an API
        exception escapes this call, the outer loop can log the exception but has
        no command to send, leaving the game stuck on the same state forever.
        This helper keeps API failures inside the decision layer so callers can
        fall back to a legal action and the run can continue.
        """
        last_exc = None

        for attempt in range(1, LLM_MAX_ATTEMPTS + 1):
            started = time.perf_counter()
            try:
                response = self.client.responses.create(
                    model=MODEL,
                    reasoning={"effort": effort},
                    input=prompt,
                )
                latency_ms = round((time.perf_counter() - started) * 1000, 2)

                if attempt > 1:
                    self.log_run_event(
                        "LLM_API_RECOVERED",
                        game_state,
                        decision_type=label,
                        successful_attempt=attempt,
                        latency_ms=latency_ms,
                    )

                return response, latency_ms

            except Exception as exc:
                last_exc = exc
                latency_ms = round((time.perf_counter() - started) * 1000, 2)

                self.log_debug(
                    f"LLM API error during {label} "
                    f"(attempt {attempt}/{LLM_MAX_ATTEMPTS}): "
                    f"{type(exc).__name__}: {exc}"
                )
                self.log_run_event(
                    "LLM_API_ERROR",
                    game_state,
                    decision_type=label,
                    attempt=attempt,
                    max_attempts=LLM_MAX_ATTEMPTS,
                    latency_ms=latency_ms,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )

                if attempt < LLM_MAX_ATTEMPTS:
                    time.sleep(LLM_RETRY_DELAY_SECONDS * attempt)

        self.log_debug(
            f"LLM API failed for {label} after {LLM_MAX_ATTEMPTS} attempts; "
            "using legal fallback action."
        )
        self.log_run_event(
            "LLM_API_FAILED",
            game_state,
            decision_type=label,
            attempts=LLM_MAX_ATTEMPTS,
            error_type=type(last_exc).__name__ if last_exc else None,
            error_message=str(last_exc) if last_exc else None,
        )
        return None, None

    def ask_index(
        self,
        label,
        prompt,
        count,
        game_state=None,
        effort="low",
        fallback=0,
        legal_actions=None,
    ):
        if count <= 0:
            raise ValueError("ask_index received no legal options")

        fallback = min(max(fallback, 0), count - 1)

        if not self.use_llm:
            self.log_run_event(
                "LLM_CALL_SKIPPED_TEST_MODE",
                game_state,
                decision_type=label,
                legal_actions=legal_actions,
                selected_index=fallback,
            )
            return fallback

        response, latency_ms = self.call_llm(
            label,
            prompt,
            game_state=game_state,
            effort=effort,
        )

        # If all API attempts failed, return a legal fallback instead of letting
        # the exception escape and deadlocking CommunicationMod.
        if response is None:
            self.log_run_event(
                "LLM_CALL",
                game_state,
                decision_type=label,
                legal_actions=legal_actions,
                legal_action_count=count,
                raw_answer=None,
                selected_index=fallback,
                fallback_used=True,
                fallback_reason="api_failure",
                latency_ms=None,
                input_tokens=None,
                output_tokens=None,
            )
            return fallback

        answer = response.output_text.strip()
        input_tokens, output_tokens = self.get_usage(response)

        fallback_used = False
        try:
            index = int(answer)
            if not 0 <= index < count:
                raise ValueError
        except ValueError:
            index = fallback
            fallback_used = True

        self.log_debug("")
        self.log_debug(f"=== {label} ===")
        self.log_debug(f"GPT answer: {answer}")
        self.log_debug(f"Selected index: {index}")
        self.log_debug(f"Fallback used: {fallback_used}")
        self.log_debug(f"Latency ms: {latency_ms}")
        self.log_debug(f"Input tokens: {input_tokens}")
        self.log_debug(f"Output tokens: {output_tokens}")

        self.log_run_event(
            "LLM_CALL",
            game_state,
            decision_type=label,
            legal_actions=legal_actions,
            legal_action_count=count,
            raw_answer=answer,
            selected_index=index,
            fallback_used=fallback_used,
            reasoning_effort=effort,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            prompt_characters=len(prompt),
        )

        return index

    # --------------------------------------------------------
    # RUN MANAGEMENT
    # --------------------------------------------------------

    def reset_for_new_run(self):
        self.entered_shop_rooms.clear()
        self.pending_grid_context = None
        self.last_screen_type = None
        self.last_game_state = None
        self.last_combat_game_state = None
        self.run_end_logged = False
        self.tracked_keys = {"ruby": False, "emerald": False, "sapphire": False}
        self.pending_key_acquisition = None
        self.last_grid_fingerprint = None
        self.last_grid_command = None

    def cache_active_state(self, game_state):
        # Each stdin line is parsed into a fresh dict and the controller never mutates it,
        # so retaining the latest object is sufficient. Deep-copying the entire map/deck/
        # combat state every action caused needless CPU and allocation pressure.

        # A pending key action is committed only once CommunicationMod responds with the
        # next valid in-game state. This works even on older CommunicationMod builds that
        # omit the documented `keys` field.
        if self.pending_key_acquisition:
            key = self.pending_key_acquisition
            self.tracked_keys[key] = True
            self.pending_key_acquisition = None
            self.log_run_event(
                "KEY_TRACK_UPDATE",
                game_state,
                acquired_key=key,
                tracked_keys=dict(self.tracked_keys),
                source="controller_inference",
            )

        self.sync_keys_from_state(game_state)
        self.last_game_state = game_state
        if game_state.get("room_phase") == "COMBAT" and game_state.get("combat_state"):
            self.last_combat_game_state = game_state

    def finalize_run(self, game_state=None, victory=None, score=None, reason=None):
        if self.run_end_logged:
            return

        source = game_state or self.last_game_state or {}
        combat_source = self.last_combat_game_state or source
        combat = combat_source.get("combat_state", {}) or {}

        if victory is None:
            victory = False
        result = "WIN" if victory else "LOSS"

        enemies = []
        for monster in combat.get("monsters", []) or []:
            enemies.append(
                {
                    "name": monster.get("name"),
                    "current_hp": monster.get("current_hp"),
                    "max_hp": monster.get("max_hp"),
                    "is_gone": monster.get("is_gone"),
                }
            )

        completed_run_number = self.completed_run_count + 1

        self.log_run_event(
            "RUN_END",
            source,
            result=result,
            end_reason=reason or ("VICTORY" if victory else "DEATH_OR_EXIT"),
            score=score,
            combat_turn=combat.get("turn"),
            enemies=enemies,
            final_deck=[display_card_name(c) for c in (source.get("deck", []) or [])],
            final_relics=[r.get("name") for r in (source.get("relics", []) or [])],
            final_potions=[
                p.get("name")
                for p in (source.get("potions", []) or [])
                if p.get("id") != "Potion Slot"
            ],
            final_keys=self.get_effective_keys(source),
            completed_run_number=completed_run_number,
            target_completed_runs=MAX_COMPLETED_RUNS,
        )
        self.completed_run_count = completed_run_number
        self.run_end_logged = True

        if self.completed_run_count >= MAX_COMPLETED_RUNS:
            self.experiment_complete = True
            self.log_run_event(
                "EXPERIMENT_COMPLETE",
                source,
                completed_runs=self.completed_run_count,
                target_completed_runs=MAX_COMPLETED_RUNS,
                message="Baseline batch complete; no further runs will be started.",
            )
            self.log_debug(
                f"BASELINE BATCH COMPLETE: {self.completed_run_count}/"
                f"{MAX_COMPLETED_RUNS} completed runs. Waiting at menu."
            )

    # --------------------------------------------------------
    # GENERIC ACTION BUILDERS
    # --------------------------------------------------------

    def build_potion_actions(self, game_state, include_discard=True):
        actions = []
        monsters = live_monsters(game_state)

        for slot, potion in actual_potions(game_state):
            name = potion.get("name", f"Potion {slot}")

            if potion.get("can_use", False):
                if potion.get("requires_target", False):
                    for monster_index, monster in monsters:
                        actions.append(
                            {
                                "command": f"POTION use {slot} {monster_index}",
                                "description": f"Use {name} on {monster.get('name')}",
                            }
                        )
                else:
                    actions.append(
                        {
                            "command": f"POTION use {slot}",
                            "description": f"Use {name}",
                        }
                    )

            if include_discard and potion.get("can_discard", False):
                actions.append(
                    {
                        "command": f"POTION discard {slot}",
                        "description": f"Discard {name} from potion slot {slot}",
                    }
                )

        return actions

    def maybe_use_out_of_combat_potion(self, game_state, available_commands):
        if "potion" not in available_commands:
            return None
        if game_state.get("room_phase") == "COMBAT":
            return None

        potion_actions = [
            a
            for a in self.build_potion_actions(game_state, include_discard=False)
            if a["command"].startswith("POTION use")
        ]
        if not potion_actions:
            return None

        actions = potion_actions + [
            {"command": None, "description": "Do not use a potion right now"}
        ]
        descriptions = [a["description"] for a in actions]

        prompt = f"""
You are playing Slay the Spire as Ironclad.

Before the current non-combat decision, one or more potions are currently usable.
Decide whether using one now improves the probability of winning the run.

HP: {game_state.get('current_hp')}/{game_state.get('max_hp')}
Act: {game_state.get('act')}
Floor: {game_state.get('floor')}
Boss: {game_state.get('act_boss')}

POTIONS
{format_potions(game_state)}

LEGAL PRE-ACTIONS
{chr(10).join(f'{i}: {d}' for i, d in enumerate(descriptions))}

Do not waste a potion without a concrete benefit.
Return ONLY the number.
"""
        fallback = len(actions) - 1
        index = self.ask_index(
            "OUT_OF_COMBAT_POTION_DECISION",
            prompt,
            len(actions),
            game_state=game_state,
            fallback=fallback,
            legal_actions=descriptions,
        )
        selected = actions[index]
        if selected["command"] is None:
            return None

        return self.action(
            selected["command"],
            game_state,
            "OUT_OF_COMBAT_POTION_DECISION",
            "LLM",
            legal_actions=descriptions,
            selected_action=selected["description"],
        )

    def choose_action(
        self,
        label,
        prompt,
        actions,
        game_state,
        fallback=0,
        effort="low",
    ):
        descriptions = [a["description"] for a in actions]
        index = self.ask_index(
            label,
            prompt,
            len(actions),
            game_state=game_state,
            effort=effort,
            fallback=fallback,
            legal_actions=descriptions,
        )
        return actions[index]

    # --------------------------------------------------------
    # EVENT
    # --------------------------------------------------------

    def build_event_actions(self, game_state):
        choices = game_state.get("choice_list", []) or []
        screen_state = game_state.get("screen_state", {}) or {}
        options = screen_state.get("options", []) or []

        option_by_choice_index = {}
        for option in options:
            if option.get("disabled", False):
                continue
            if "choice_index" in option:
                option_by_choice_index[int(option["choice_index"])] = option

        actions = []
        for i, choice in enumerate(choices):
            option = option_by_choice_index.get(i, {})
            text = option.get("text") or option.get("label") or choice
            actions.append(
                {
                    "command": f"CHOOSE {i}",
                    "description": str(text),
                    "choice": choice,
                    "choice_index": i,
                }
            )
        return actions

    def choose_event(self, game_state, actions):
        screen_state = game_state.get("screen_state", {}) or {}
        event_name = screen_state.get("event_name", "Unknown Event")
        event_id = screen_state.get("event_id", "")
        body = screen_state.get("body_text", "")
        descriptions = [a["description"] for a in actions]

        if "match" in str(event_name).lower() and "keep" in str(event_name).lower():
            self.log_run_event(
                "OBSERVATION_LIMITATION",
                game_state,
                limitation="MATCH_AND_KEEP_PARTIAL_STATE",
                detail=(
                    "CommunicationMod exposes selectable positions/revealed card IDs, "
                    "but does not transmit the complete hidden board state."
                ),
            )

        prompt = f"""
You are playing Slay the Spire as Ironclad.
Your objective is to maximize the probability of winning the entire run.

EVENT
Name: {event_name}
ID: {event_id}
Description: {body}

RUN STATE
Act: {game_state.get('act')}
Floor: {game_state.get('floor')}
HP: {game_state.get('current_hp')}/{game_state.get('max_hp')}
Gold: {game_state.get('gold')}
Boss: {game_state.get('act_boss')}
Keys: {format_keys(game_state)}

RELICS
{format_relics(game_state)}

POTIONS
{format_potions(game_state)}

DECK
{format_deck(game_state.get('deck', []))}

LEGAL EVENT OPTIONS
{chr(10).join(f'{i}: {d}' for i, d in enumerate(descriptions))}

Choose the option that maximizes long-term run survival.
Return ONLY the number.
"""
        return self.choose_action(
            "EVENT_DECISION",
            prompt,
            actions,
            game_state,
            fallback=0,
        )

    # --------------------------------------------------------
    # MAP
    # --------------------------------------------------------

    def ask_map_choice(self, prompt, actions, game_state, fallback=0):
        """
        Map nodes use numeric x-coordinates, so asking for a numeric action index is
        ambiguous (e.g. output `3` can mean action index 3 or x=3). Map decisions use
        letter labels instead. If the model still returns an x-coordinate, recover it
        explicitly rather than silently taking action 0.
        """
        count = len(actions)
        if count <= 0:
            raise ValueError("ask_map_choice received no legal options")

        fallback = min(max(fallback, 0), count - 1)
        labels = [chr(ord("A") + i) for i in range(count)]
        legal_actions = [f"{labels[i]}: {a['description']}" for i, a in enumerate(actions)]

        if not self.use_llm:
            self.log_run_event(
                "LLM_CALL_SKIPPED_TEST_MODE",
                game_state,
                decision_type="MAP_DECISION",
                legal_actions=legal_actions,
                selected_index=fallback,
                selected_label=labels[fallback],
                decoder_mode="test_fallback",
            )
            return fallback

        response, latency_ms = self.call_llm(
            "MAP_DECISION",
            prompt,
            game_state=game_state,
            effort="low",
        )

        if response is None:
            selected_index = fallback
            decoder_mode = "api_failure_fallback"
            self.log_run_event(
                "LLM_CALL",
                game_state,
                decision_type="MAP_DECISION",
                legal_actions=legal_actions,
                legal_action_count=count,
                raw_answer=None,
                selected_index=selected_index,
                selected_label=labels[selected_index],
                decoder_mode=decoder_mode,
                fallback_used=True,
                fallback_reason="api_failure",
                latency_ms=None,
                input_tokens=None,
                output_tokens=None,
            )
            return selected_index

        answer = response.output_text.strip()
        input_tokens, output_tokens = self.get_usage(response)

        selected_index = None
        decoder_mode = None
        cleaned = answer.strip().upper().strip(" .,:;()[]{}")

        # Preferred protocol: one letter only.
        if cleaned in labels:
            selected_index = labels.index(cleaned)
            decoder_mode = "letter"
        else:
            # Be tolerant of short forms such as "A." or "A - ...".
            first = cleaned[:1]
            if first in labels and (len(cleaned) == 1 or not cleaned[1:2].isalpha()):
                selected_index = labels.index(first)
                decoder_mode = "letter_recovered"

        # Recovery for the exact failure observed in v0.2.1: the LLM returned the
        # desired map x-coordinate instead of the requested action index. Numeric
        # outputs are interpreted as coordinates, never as indexes, because this
        # function's protocol is letter-based.
        if selected_index is None:
            coord_text = answer.strip().lower()
            if coord_text.startswith("x="):
                coord_text = coord_text[2:].strip()
            try:
                coordinate = int(coord_text)
            except ValueError:
                coordinate = None

            if coordinate is not None:
                matches = []
                for i, action in enumerate(actions):
                    choice = str(action.get("choice", "")).lower()
                    if choice.startswith("x="):
                        try:
                            if int(choice[2:]) == coordinate:
                                matches.append(i)
                        except ValueError:
                            pass
                if len(matches) == 1:
                    selected_index = matches[0]
                    decoder_mode = "x_coordinate_recovery"

        fallback_used = selected_index is None
        if fallback_used:
            selected_index = fallback
            decoder_mode = "fallback"

        self.log_debug("")
        self.log_debug("=== MAP_DECISION ===")
        self.log_debug(f"GPT answer: {answer}")
        self.log_debug(f"Selected label: {labels[selected_index]}")
        self.log_debug(f"Selected index: {selected_index}")
        self.log_debug(f"Decoder mode: {decoder_mode}")
        self.log_debug(f"Fallback used: {fallback_used}")
        self.log_debug(f"Latency ms: {latency_ms}")

        self.log_run_event(
            "LLM_CALL",
            game_state,
            decision_type="MAP_DECISION",
            legal_actions=legal_actions,
            legal_action_count=count,
            raw_answer=answer,
            selected_index=selected_index,
            selected_label=labels[selected_index],
            fallback_used=fallback_used,
            decoder_mode=decoder_mode,
            reasoning_effort="low",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            prompt_characters=len(prompt),
        )
        return selected_index

    def choose_map(self, game_state):
        choices = game_state.get("choice_list", []) or []
        actions = [
            {
                "command": f"CHOOSE {choice}",
                "description": f"Move to {choice}",
                "choice": choice,
            }
            for choice in choices
        ]

        map_lines = []
        for node in sorted(
            game_state.get("map", []) or [],
            key=lambda n: (n.get("y", 0), n.get("x", 0)),
        ):
            children = ", ".join(
                f"x={c.get('x')},y={c.get('y')}"
                for c in (node.get("children", []) or [])
            )
            map_lines.append(
                f"x={node.get('x')},y={node.get('y')} "
                f"type={node.get('symbol')} -> [{children}]"
            )

        labels = [chr(ord("A") + i) for i in range(len(actions))]
        prompt = f"""
You are playing Slay the Spire as Ironclad.
Choose the next map node to maximize the probability of winning the run.

HP: {game_state.get('current_hp')}/{game_state.get('max_hp')}
Gold: {game_state.get('gold')}
Act: {game_state.get('act')}
Floor: {game_state.get('floor')}
Boss: {game_state.get('act_boss')}
Keys: {format_keys(game_state)}

RELICS
{format_relics(game_state)}

POTIONS
{format_potions(game_state)}

DECK
{format_deck(game_state.get('deck', []))}

MAP SYMBOLS
M=normal combat, E=elite, R=rest, ?=event, $=shop, T=treasure

FULL MAP
{chr(10).join(map_lines)}

LEGAL ACTIONS
{chr(10).join(f'{labels[i]}: {a["description"]}' for i, a in enumerate(actions))}

Consider the entire future route, HP, deck strength, elites, campfires,
shops, potions, relics, keys, and the Act boss.

IMPORTANT OUTPUT FORMAT:
Return ONLY the action LETTER ({', '.join(labels)}).
Do NOT return the x-coordinate and do NOT return a number.
"""
        index = self.ask_map_choice(prompt, actions, game_state, fallback=0)
        return actions[index]

    # --------------------------------------------------------
    # REST
    # --------------------------------------------------------

    def choose_rest(self, game_state):
        choices = game_state.get("choice_list", []) or []
        explanations = {
            "rest": "Heal HP.",
            "smith": "Upgrade one card; usually opens a GRID selection.",
            "recall": "Take the Ruby Key.",
            "lift": "Use Girya to gain permanent Strength.",
            "toke": "Use Peace Pipe to remove a card; opens GRID.",
            "dig": "Use Shovel to obtain a relic.",
        }
        actions = []
        for choice in choices:
            actions.append(
                {
                    "command": f"CHOOSE {choice}",
                    "description": f"{choice}: {explanations.get(choice.lower(), 'Use this campfire option.')}",
                    "choice": choice,
                }
            )

        hp = game_state.get("current_hp") or 0
        max_hp = game_state.get("max_hp") or 0
        fallback = 0
        if max_hp and hp <= max_hp * 0.35 and "rest" in lower_list(choices):
            fallback = lower_list(choices).index("rest")
        elif "smith" in lower_list(choices):
            fallback = lower_list(choices).index("smith")

        descriptions = [a["description"] for a in actions]
        prompt = f"""
You are playing Slay the Spire as Ironclad at a campfire.
Choose the option that maximizes the probability of winning the entire run.

HP: {hp}/{max_hp}
Act: {game_state.get('act')}
Floor: {game_state.get('floor')}
Boss: {game_state.get('act_boss')}
Keys: {format_keys(game_state)}

RELICS
{format_relics(game_state)}

POTIONS
{format_potions(game_state)}

DECK
{format_deck(game_state.get('deck', []))}

LEGAL CAMPFIRE ACTIONS
{chr(10).join(f'{i}: {d}' for i, d in enumerate(descriptions))}

Do not automatically Rest just because HP is missing. Balance immediate survival
against long-term value and upcoming danger.
Return ONLY the number.
"""
        return self.choose_action(
            "REST_DECISION",
            prompt,
            actions,
            game_state,
            fallback=fallback,
        )

    # --------------------------------------------------------
    # GRID
    # --------------------------------------------------------

    def grid_state_fingerprint(self, game_state):
        """Compact identity for detecting a GRID state that did not progress."""
        screen_state = game_state.get("screen_state", {}) or {}
        selected = []
        for card in screen_state.get("selected_cards", []) or []:
            if isinstance(card, dict):
                selected.append(card.get("uuid") or display_card_name(card))
            else:
                selected.append(str(card))

        payload = {
            "seed": game_state.get("seed"),
            "floor": game_state.get("floor"),
            "room_type": game_state.get("room_type"),
            "choices": game_state.get("choice_list", []) or [],
            "selected": selected,
            "num_cards": screen_state.get("num_cards"),
            "any_number": screen_state.get("any_number"),
            "confirm_up": screen_state.get("confirm_up"),
            "for_upgrade": screen_state.get("for_upgrade"),
            "for_transform": screen_state.get("for_transform"),
            "for_purge": screen_state.get("for_purge"),
            "context": self.pending_grid_context,
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)

    def build_grid_actions(self, game_state, available_commands):
        choices = game_state.get("choice_list", []) or []
        screen_state = game_state.get("screen_state", {}) or {}
        cards = screen_state.get("cards", []) or []
        selected_cards = screen_state.get("selected_cards", []) or []

        # A selected card can remain visible in CommunicationMod's GRID card
        # list. Do not offer it again when we can identify it by UUID; otherwise
        # the controller may repeatedly toggle/reselect the same card.
        selected_uuids = {
            c.get("uuid")
            for c in selected_cards
            if isinstance(c, dict) and c.get("uuid")
        }

        actions = []
        for i, choice in enumerate(choices):
            card = cards[i] if i < len(cards) else None
            if card and card.get("uuid") in selected_uuids:
                continue

            name = display_card_name(card) if card else choice
            actions.append(
                {
                    "command": f"CHOOSE {i}",
                    "description": f"Select {name}",
                    "card": card,
                }
            )

        if "confirm" in available_commands:
            actions.append(
                {"command": "CONFIRM", "description": "Confirm current GRID selection"}
            )
        if "cancel" in available_commands or "return" in available_commands:
            # RETURN is the canonical CommunicationMod command; CANCEL is an alias.
            actions.append(
                {"command": "RETURN", "description": "Cancel this GRID selection"}
            )
        return actions

    def recover_grid_no_progress(self, game_state, actions, selected):
        """Avoid issuing the same CHOOSE forever when a GRID state is unchanged."""
        fingerprint = self.grid_state_fingerprint(game_state)
        selected_command = selected.get("command")

        if (
            fingerprint == self.last_grid_fingerprint
            and selected_command == self.last_grid_command
        ):
            choose_alternatives = [
                action
                for action in actions
                if str(action.get("command", "")).startswith("CHOOSE ")
                and action.get("command") != selected_command
            ]

            if choose_alternatives:
                recovered = choose_alternatives[0]
            else:
                recovered = next(
                    (a for a in actions if a.get("command") == "CONFIRM"),
                    None,
                ) or next(
                    (a for a in actions if a.get("command") == "RETURN"),
                    None,
                )

            if recovered is not None:
                self.log_debug(
                    "GRID_NO_PROGRESS_RECOVERY: "
                    f"unchanged GRID repeated {selected_command}; "
                    f"using {recovered.get('command')} instead."
                )
                self.log_run_event(
                    "GRID_NO_PROGRESS_RECOVERY",
                    game_state,
                    repeated_command=selected_command,
                    recovery_command=recovered.get("command"),
                    recovery_action=recovered.get("description"),
                )
                selected = recovered
                selected_command = recovered.get("command")

        self.last_grid_fingerprint = fingerprint
        self.last_grid_command = selected_command
        return selected

    def choose_grid(self, game_state, available_commands, actions):
        screen_state = game_state.get("screen_state", {}) or {}
        if screen_state.get("for_purge"):
            purpose = "Permanently remove selected card(s) from the deck."
        elif screen_state.get("for_transform"):
            purpose = "Transform selected card(s)."
        elif screen_state.get("for_upgrade"):
            purpose = "Upgrade selected card(s)."
        else:
            purpose = self.pending_grid_context or "Choose card(s) for the current effect."

        descriptions = [a["description"] for a in actions]
        prompt = f"""
You are playing Slay the Spire as Ironclad.
A GRID card-selection screen is active.

PURPOSE
{purpose}

SELECTION STATE
Required cards: {screen_state.get('num_cards')}
Any number allowed: {screen_state.get('any_number')}
Already selected: {len(screen_state.get('selected_cards', []) or [])}
Confirm screen up: {screen_state.get('confirm_up')}

HP: {game_state.get('current_hp')}/{game_state.get('max_hp')}
Boss: {game_state.get('act_boss')}

RELICS
{format_relics(game_state)}

DECK
{format_deck(game_state.get('deck', []))}

LEGAL ACTIONS
{chr(10).join(f'{i}: {d}' for i, d in enumerate(descriptions))}

Choose exactly one action now. If multiple selections are required, the updated
state will be evaluated again after this action.
Return ONLY the number.
"""

        fallback = 0
        if screen_state.get("for_purge") or screen_state.get("for_transform"):
            for i, action in enumerate(actions):
                card = action.get("card")
                if card and card.get("id") == "Strike_R":
                    fallback = i
                    break

        return self.choose_action(
            "GRID_DECISION",
            prompt,
            actions,
            game_state,
            fallback=fallback,
        )

    # --------------------------------------------------------
    # HAND SELECT
    # --------------------------------------------------------

    def build_hand_select_actions(self, game_state, available_commands):
        choices = game_state.get("choice_list", []) or []
        screen_state = game_state.get("screen_state", {}) or {}
        hand = screen_state.get("hand", []) or []

        actions = []
        for i, choice in enumerate(choices):
            card = hand[i] if i < len(hand) else None
            name = display_card_name(card) if card else choice
            actions.append(
                {
                    "command": f"CHOOSE {i}",
                    "description": f"Select {name}",
                    "card": card,
                }
            )

        if "confirm" in available_commands:
            actions.append(
                {"command": "CONFIRM", "description": "Finish hand-card selection"}
            )
        return actions

    def choose_hand_select(self, game_state, actions):
        screen_state = game_state.get("screen_state", {}) or {}
        combat = game_state.get("combat_state", {}) or {}
        card_in_play = combat.get("card_in_play")
        resolving = display_card_name(card_in_play) if card_in_play else "Unknown effect"
        descriptions = [a["description"] for a in actions]

        prompt = f"""
You are playing Slay the Spire as Ironclad.
A combat effect is asking you to select cards from your hand.

RESOLVING CARD / EFFECT
{resolving}

Use your knowledge of that effect to infer whether selected cards are being
exhausted, discarded, moved, duplicated, or otherwise affected.

Max cards: {screen_state.get('max_cards')}
Already selected: {len(screen_state.get('selected', []) or [])}
Can pick zero: {screen_state.get('can_pick_zero')}

PLAYER
{combat.get('player', {})}

ENEMIES
{format_monsters(game_state)}

DRAW PILE
{format_deck(combat.get('draw_pile', []))}

DISCARD PILE
{format_deck(combat.get('discard_pile', []))}

EXHAUST PILE
{format_deck(combat.get('exhaust_pile', []))}

LEGAL ACTIONS
{chr(10).join(f'{i}: {d}' for i, d in enumerate(descriptions))}

Choose exactly one action now. The state will refresh after each selection.
Return ONLY the number.
"""

        fallback = 0
        return self.choose_action(
            "HAND_SELECT_DECISION",
            prompt,
            actions,
            game_state,
            fallback=fallback,
        )

    # --------------------------------------------------------
    # CARD REWARD
    # --------------------------------------------------------

    def build_card_reward_actions(self, game_state, available_commands):
        choices = game_state.get("choice_list", []) or []
        screen_state = game_state.get("screen_state", {}) or {}
        cards = screen_state.get("cards", []) or []

        actions = []
        for i, choice in enumerate(choices):
            if i < len(cards):
                card = cards[i]
                description = f"Take {display_card_name(card)}"
            elif str(choice).lower() == "bowl":
                card = None
                description = "Use Singing Bowl instead of taking a card (+2 Max HP)"
            else:
                card = None
                description = f"Choose card-reward option {choice}"

            actions.append(
                {
                    "command": f"CHOOSE {i}",
                    "description": description,
                    "card": card,
                    "choice": choice,
                }
            )

        if "skip" in available_commands or screen_state.get("skip_available", False):
            actions.append(
                {
                    "command": "SKIP",
                    "description": "Skip this card reward",
                    "card": None,
                    "choice": "skip",
                }
            )

        return actions

    def choose_card_reward(self, game_state, actions):
        descriptions = [a["description"] for a in actions]
        prompt = f"""
You are playing Slay the Spire as Ironclad.
Choose the card-reward action that maximizes the probability of winning the run.

HP: {game_state.get('current_hp')}/{game_state.get('max_hp')}
Act: {game_state.get('act')}
Floor: {game_state.get('floor')}
Boss: {game_state.get('act_boss')}
Keys: {format_keys(game_state)}

RELICS
{format_relics(game_state)}

DECK
{format_deck(game_state.get('deck', []))}

LEGAL ACTIONS
{chr(10).join(f'{i}: {d}' for i, d in enumerate(descriptions))}

Skipping is valid. If Singing Bowl is available, compare +2 Max HP against the
actual value of each card for the current deck.
Return ONLY the number.
"""

        fallback = 0
        for i, action in enumerate(actions):
            if action["command"] == "SKIP":
                fallback = i
                break

        return self.choose_action(
            "CARD_REWARD_DECISION",
            prompt,
            actions,
            game_state,
            fallback=fallback,
        )

    # --------------------------------------------------------
    # BOSS RELIC REWARD
    # --------------------------------------------------------

    def build_boss_reward_actions(self, game_state, available_commands):
        choices = game_state.get("choice_list", []) or []
        screen_state = game_state.get("screen_state", {}) or {}
        relics = screen_state.get("relics", []) or []

        actions = []
        for i, choice in enumerate(choices):
            relic = relics[i] if i < len(relics) else None
            name = relic.get("name") if relic else choice
            actions.append(
                {
                    "command": f"CHOOSE {i}",
                    "description": f"Take boss relic {name}",
                    "relic": relic,
                }
            )

        if "skip" in available_commands:
            actions.append(
                {"command": "SKIP", "description": "Skip all boss relics", "relic": None}
            )
        return actions

    def choose_boss_reward(self, game_state, actions):
        descriptions = [a["description"] for a in actions]
        prompt = f"""
You are playing Slay the Spire as Ironclad and choosing a boss relic.
This is a major long-horizon decision. Maximize the probability of winning the entire run.

Act just completed: {game_state.get('act')}
Floor: {game_state.get('floor')}
HP: {game_state.get('current_hp')}/{game_state.get('max_hp')}
Gold: {game_state.get('gold')}
Keys: {format_keys(game_state)}

CURRENT RELICS
{format_relics(game_state)}

POTIONS
{format_potions(game_state)}

DECK
{format_deck(game_state.get('deck', []))}

LEGAL ACTIONS
{chr(10).join(f'{i}: {d}' for i, d in enumerate(descriptions))}

Consider energy, card-play restrictions, enemy-intent visibility, deck cost curve,
synergies, future elites, and future Acts. Do not choose an energy relic without
considering its downside. Skipping should be rare.
Return ONLY the number.
"""
        return self.choose_action(
            "BOSS_REWARD_DECISION",
            prompt,
            actions,
            game_state,
            fallback=0,
        )

    # --------------------------------------------------------
    # SHOP
    # --------------------------------------------------------

    def format_shop_inventory(self, game_state):
        screen_state = game_state.get("screen_state", {}) or {}
        lines = ["CARDS:"]
        for card in screen_state.get("cards", []) or []:
            lines.append(f"- {display_card_name(card)}: {card.get('price')} gold")
        lines.append("\nRELICS:")
        for relic in screen_state.get("relics", []) or []:
            lines.append(f"- {relic.get('name')}: {relic.get('price')} gold")
        lines.append("\nPOTIONS:")
        for potion in screen_state.get("potions", []) or []:
            lines.append(f"- {potion.get('name')}: {potion.get('price')} gold")
        if screen_state.get("purge_available", False):
            lines.append(f"\nCARD REMOVAL: {screen_state.get('purge_cost')} gold")
        else:
            lines.append("\nCARD REMOVAL: unavailable")
        return "\n".join(lines)

    def build_shop_actions(self, game_state, available_commands):
        screen_state = game_state.get("screen_state", {}) or {}
        choices = game_state.get("choice_list", []) or []
        cards = screen_state.get("cards", []) or []
        relics = screen_state.get("relics", []) or []
        shop_potions = screen_state.get("potions", []) or []

        card_lookup = {str(c.get("name", "")).lower(): c for c in cards}
        relic_lookup = {str(r.get("name", "")).lower(): r for r in relics}
        potion_lookup = {str(p.get("name", "")).lower(): p for p in shop_potions}

        full_potions = not has_empty_potion_slot(game_state)
        affordable_potion_choice_present = any(
            str(choice).lower() in potion_lookup for choice in choices
        )

        actions = []
        for i, choice in enumerate(choices):
            key = str(choice).lower()

            if key == "purge":
                actions.append(
                    {
                        "command": f"CHOOSE {i}",
                        "description": f"Buy card removal for {screen_state.get('purge_cost')} gold",
                        "kind": "purge",
                    }
                )
            elif key in card_lookup:
                card = card_lookup[key]
                actions.append(
                    {
                        "command": f"CHOOSE {i}",
                        "description": f"Buy {display_card_name(card)} for {card.get('price')} gold",
                        "kind": "card",
                    }
                )
            elif key in relic_lookup:
                relic = relic_lookup[key]
                actions.append(
                    {
                        "command": f"CHOOSE {i}",
                        "description": f"Buy relic {relic.get('name')} for {relic.get('price')} gold",
                        "kind": "relic",
                    }
                )
            elif key in potion_lookup:
                potion = potion_lookup[key]
                if full_potions:
                    # CommunicationMod still reports affordable shop potions even when
                    # the inventory is full. Clicking one can fail to change state.
                    continue
                actions.append(
                    {
                        "command": f"CHOOSE {i}",
                        "description": f"Buy potion {potion.get('name')} for {potion.get('price')} gold",
                        "kind": "potion",
                    }
                )
            else:
                actions.append(
                    {
                        "command": f"CHOOSE {i}",
                        "description": f"Choose merchant option {choice}",
                        "kind": "other",
                    }
                )

        # If affordable potions exist but the belt is full, expose explicit discard
        # actions. After the discard, the shop is re-evaluated and the potion can be bought.
        if full_potions and affordable_potion_choice_present and "potion" in available_commands:
            for slot, potion in actual_potions(game_state):
                if potion.get("can_discard", False):
                    actions.append(
                        {
                            "command": f"POTION discard {slot}",
                            "description": (
                                f"Discard {potion.get('name')} from slot {slot} to make room "
                                "for a shop potion"
                            ),
                            "kind": "discard_potion",
                        }
                    )

        if "leave" in available_commands:
            actions.append(
                {"command": "LEAVE", "description": "Leave the merchant", "kind": "leave"}
            )
        return actions

    def choose_shop(self, game_state, actions):
        descriptions = [a["description"] for a in actions]
        prompt = f"""
You are playing Slay the Spire as Ironclad at a merchant.
Choose exactly ONE action. The shop will be re-evaluated after the action.

HP: {game_state.get('current_hp')}/{game_state.get('max_hp')}
Gold: {game_state.get('gold')}
Act: {game_state.get('act')}
Floor: {game_state.get('floor')}
Boss: {game_state.get('act_boss')}
Keys: {format_keys(game_state)}

RELICS
{format_relics(game_state)}

POTIONS
{format_potions(game_state)}

DECK
{format_deck(game_state.get('deck', []))}

SHOP INVENTORY
{self.format_shop_inventory(game_state)}

LEGAL ACTIONS
{chr(10).join(f'{i}: {d}' for i, d in enumerate(descriptions))}

Do not buy something merely because it is affordable. Consider removal, relic
synergy, potion replacement, future shops, current HP, elites, and the boss.
Return ONLY the number.
"""

        fallback = 0
        for i, action in enumerate(actions):
            if action.get("kind") == "leave":
                fallback = i
                break

        return self.choose_action(
            "SHOP_DECISION",
            prompt,
            actions,
            game_state,
            fallback=fallback,
        )

    # --------------------------------------------------------
    # COMBAT
    # --------------------------------------------------------

    def build_combat_actions(self, game_state, available_commands):
        combat = game_state.get("combat_state", {}) or {}
        hand = combat.get("hand", []) or []
        monsters = combat.get("monsters", []) or []
        actions = []

        if "play" in available_commands:
            for hand_index, card in enumerate(hand, start=1):
                if not card.get("is_playable", False):
                    continue

                if card.get("has_target", False):
                    for monster_index, monster in enumerate(monsters):
                        if monster.get("is_gone", False) or monster.get("half_dead", False):
                            continue
                        actions.append(
                            {
                                "command": f"PLAY {hand_index} {monster_index}",
                                "description": (
                                    f"Play {display_card_name(card)} on {monster.get('name')} "
                                    f"({monster.get('current_hp')} HP)"
                                ),
                                "kind": "card",
                            }
                        )
                else:
                    actions.append(
                        {
                            "command": f"PLAY {hand_index}",
                            "description": f"Play {display_card_name(card)}",
                            "kind": "card",
                        }
                    )

        if "potion" in available_commands:
            for action in self.build_potion_actions(game_state, include_discard=True):
                action = dict(action)
                action["kind"] = "potion"
                actions.append(action)

        if "end" in available_commands:
            actions.append({"command": "END", "description": "End turn", "kind": "end"})

        return actions

    def choose_combat(self, game_state, actions):
        combat = game_state.get("combat_state", {}) or {}
        player = combat.get("player", {}) or {}
        descriptions = [a["description"] for a in actions]

        hand_lines = []
        for i, card in enumerate(combat.get("hand", []) or [], start=1):
            hand_lines.append(
                f"{i}: {display_card_name(card)} | cost={card.get('cost')} | "
                f"type={card.get('type')} | playable={card.get('is_playable')}"
            )

        prompt = f"""
You are playing Slay the Spire as Ironclad.
Choose exactly ONE legal combat action to maximize the probability of winning the run.

TURN: {combat.get('turn')}

PLAYER
HP: {player.get('current_hp')}/{player.get('max_hp')}
Block: {player.get('block')}
Energy: {player.get('energy')}

MONSTERS
{format_monsters(game_state)}

HAND
{chr(10).join(hand_lines)}

POTIONS
{format_potions(game_state)}

DRAW PILE
{format_deck(combat.get('draw_pile', []))}

DISCARD PILE
{format_deck(combat.get('discard_pile', []))}

EXHAUST PILE
{format_deck(combat.get('exhaust_pile', []))}

LEGAL ACTIONS
{chr(10).join(f'{i}: {d}' for i, d in enumerate(descriptions))}

Consider incoming damage, kills, card order, energy, debuffs, draw, exhaust,
potion value, and HP preservation. Do not hoard a potion when using it materially
improves survival. Discarding a potion during combat is usually poor unless there
is a compelling reason.
Return ONLY the number.
"""

        fallback = 0
        for i, action in enumerate(actions):
            if action.get("kind") == "end":
                fallback = i
                break

        return self.choose_action(
            "COMBAT_DECISION",
            prompt,
            actions,
            game_state,
            fallback=fallback,
        )

    # --------------------------------------------------------
    # COMBAT / CHEST REWARDS
    # --------------------------------------------------------

    @staticmethod
    def reward_description(choice, reward):
        key = str(choice).lower()
        reward = reward or {}
        reward_type = str(reward.get("reward_type", key)).upper()

        if reward_type in {"GOLD", "STOLEN_GOLD"}:
            return f"Collect {reward.get('gold')} gold ({reward_type.lower()})"
        if reward_type == "RELIC":
            relic = reward.get("relic", {}) or {}
            return f"Take relic {relic.get('name', 'Unknown Relic')}"
        if reward_type == "POTION":
            potion = reward.get("potion", {}) or {}
            return f"Take potion {potion.get('name', 'Unknown Potion')}"
        if reward_type == "CARD":
            return "Open card reward"
        if reward_type == "SAPPHIRE_KEY":
            link = reward.get("link", {}) or {}
            return f"Take Sapphire Key instead of linked relic {link.get('name', 'Unknown Relic')}"
        if "KEY" in reward_type:
            return f"Collect {reward_type.replace('_', ' ').title()}"
        return f"Collect reward {choice}"

    def choose_sapphire_key_or_relic(self, game_state, available_commands):
        choices = game_state.get("choice_list", []) or []
        rewards = (game_state.get("screen_state", {}) or {}).get("rewards", []) or []

        sapphire_index = None
        sapphire_reward = None
        for i, choice in enumerate(choices):
            if str(choice).lower() == "sapphire_key":
                sapphire_index = i
                sapphire_reward = rewards[i] if i < len(rewards) else {}
                break

        if sapphire_index is None:
            return None

        link = (sapphire_reward or {}).get("link", {}) or {}
        linked_name = str(link.get("name", "")).lower()
        relic_index = None
        relic_reward = None

        for i, choice in enumerate(choices):
            if str(choice).lower() != "relic":
                continue
            reward = rewards[i] if i < len(rewards) else {}
            relic = reward.get("relic", {}) or {}
            if linked_name and str(relic.get("name", "")).lower() == linked_name:
                relic_index = i
                relic_reward = reward
                break

        # If CommunicationMod exposes a Sapphire Key without a linked relic choice,
        # it is not a trade-off in the current state, so collect it deterministically.
        if relic_index is None:
            return self.action(
                f"CHOOSE {sapphire_index}",
                game_state,
                "REWARD_SAPPHIRE_KEY",
                "CONTROLLER",
                legal_actions=choices,
                selected_action=self.reward_description("sapphire_key", sapphire_reward),
            )

        relic_name = ((relic_reward or {}).get("relic", {}) or {}).get("name", "Unknown Relic")
        actions = [
            {
                "command": f"CHOOSE {relic_index}",
                "description": f"Take linked relic {relic_name} and give up the Sapphire Key",
            },
            {
                "command": f"CHOOSE {sapphire_index}",
                "description": f"Take the Sapphire Key and give up {relic_name}",
            },
        ]
        descriptions = [a["description"] for a in actions]

        prompt = f"""
You are playing Slay the Spire as Ironclad.
A chest reward forces a choice between a relic and the Sapphire Key.
Choose the option that maximizes the probability of winning the entire run.

HP: {game_state.get('current_hp')}/{game_state.get('max_hp')}
Act: {game_state.get('act')}
Floor: {game_state.get('floor')}
Boss: {game_state.get('act_boss')}
Keys already held: {format_keys(game_state)}

RELICS
{format_relics(game_state)}

DECK
{format_deck(game_state.get('deck', []))}

LEGAL ACTIONS
{chr(10).join(f'{i}: {d}' for i, d in enumerate(descriptions))}

The Sapphire Key is required for Act 4, but taking it sacrifices the linked relic.
Consider whether Act 4 is still reachable and how valuable the relic is for this run.
Return ONLY the number.
"""
        selected = self.choose_action(
            "SAPPHIRE_KEY_DECISION",
            prompt,
            actions,
            game_state,
            fallback=0,
        )
        return self.action(
            selected["command"],
            game_state,
            "SAPPHIRE_KEY_DECISION",
            "LLM",
            legal_actions=descriptions,
            selected_action=selected["description"],
        )

    def choose_full_potion_reward(self, game_state, available_commands, potion_index):
        rewards = (game_state.get("screen_state", {}) or {}).get("rewards", []) or []
        reward = rewards[potion_index] if potion_index < len(rewards) else {}
        new_potion = (reward or {}).get("potion", {}) or {}
        new_name = new_potion.get("name", "reward potion")

        actions = []
        if "potion" in available_commands:
            for slot, potion in actual_potions(game_state):
                if potion.get("can_discard", False):
                    actions.append(
                        {
                            "command": f"POTION discard {slot}",
                            "description": (
                                f"Discard {potion.get('name')} from slot {slot} to make room for {new_name}"
                            ),
                        }
                    )

        if "proceed" in available_commands:
            actions.append(
                {
                    "command": "PROCEED",
                    "description": f"Skip {new_name} and keep current potions",
                }
            )

        if not actions:
            return None

        descriptions = [a["description"] for a in actions]
        prompt = f"""
You are playing Slay the Spire as Ironclad.
You received {new_name}, but all potion slots are full.
Choose whether to replace a current potion or leave the new potion behind.

HP: {game_state.get('current_hp')}/{game_state.get('max_hp')}
Act: {game_state.get('act')}
Floor: {game_state.get('floor')}
Boss: {game_state.get('act_boss')}

CURRENT POTIONS
{format_potions(game_state)}

LEGAL ACTIONS
{chr(10).join(f'{i}: {d}' for i, d in enumerate(descriptions))}

Compare the current potions with the new potion and upcoming threats.
Return ONLY the number.
"""
        fallback = len(actions) - 1
        selected = self.choose_action(
            "POTION_REWARD_REPLACEMENT_DECISION",
            prompt,
            actions,
            game_state,
            fallback=fallback,
        )
        return self.action(
            selected["command"],
            game_state,
            "POTION_REWARD_REPLACEMENT_DECISION",
            "LLM",
            legal_actions=descriptions,
            selected_action=selected["description"],
        )

    def handle_combat_reward(self, game_state, available_commands):
        choices = game_state.get("choice_list", []) or []
        rewards = (game_state.get("screen_state", {}) or {}).get("rewards", []) or []
        lowered = lower_list(choices)

        # No-downside rewards are consumed first so later strategic decisions are
        # made with an updated run state.
        for reward_name in ("gold", "stolen_gold"):
            if reward_name in lowered:
                i = lowered.index(reward_name)
                reward = rewards[i] if i < len(rewards) else {}
                return self.action(
                    f"CHOOSE {i}",
                    game_state,
                    f"REWARD_{reward_name.upper()}",
                    "CONTROLLER",
                    legal_actions=choices,
                    selected_action=self.reward_description(reward_name, reward),
                )

        # Sapphire Key is a genuine relic-vs-key trade-off and must be decided
        # before auto-collecting the linked relic.
        if "sapphire_key" in lowered:
            result = self.choose_sapphire_key_or_relic(game_state, available_commands)
            if result:
                return result

        # Other keys do not sacrifice a linked reward.
        for i, choice in enumerate(choices):
            if "key" in str(choice).lower() and str(choice).lower() != "sapphire_key":
                reward = rewards[i] if i < len(rewards) else {}
                return self.action(
                    f"CHOOSE {i}",
                    game_state,
                    "REWARD_KEY",
                    "CONTROLLER",
                    legal_actions=choices,
                    selected_action=self.reward_description(choice, reward),
                )

        if "relic" in lowered:
            i = lowered.index("relic")
            reward = rewards[i] if i < len(rewards) else {}
            return self.action(
                f"CHOOSE {i}",
                game_state,
                "REWARD_RELIC",
                "CONTROLLER",
                legal_actions=choices,
                selected_action=self.reward_description("relic", reward),
            )

        if "card" in lowered:
            i = lowered.index("card")
            return self.action(
                f"CHOOSE {i}",
                game_state,
                "REWARD_CARD_OPEN",
                "CONTROLLER",
                legal_actions=choices,
                selected_action="Open card reward",
            )

        if "potion" in lowered:
            i = lowered.index("potion")
            reward = rewards[i] if i < len(rewards) else {}
            if has_empty_potion_slot(game_state):
                return self.action(
                    f"CHOOSE {i}",
                    game_state,
                    "REWARD_POTION",
                    "CONTROLLER",
                    legal_actions=choices,
                    selected_action=self.reward_description("potion", reward),
                )
            return self.choose_full_potion_reward(game_state, available_commands, i)

        if choices and "choose" in available_commands:
            actions = []
            for i, choice in enumerate(choices):
                reward = rewards[i] if i < len(rewards) else {}
                actions.append(
                    {
                        "command": f"CHOOSE {i}",
                        "description": self.reward_description(choice, reward),
                    }
                )

            if len(actions) == 1:
                selected = actions[0]
                source = "CONTROLLER"
            else:
                descriptions = [a["description"] for a in actions]
                prompt = f"""
You are playing Slay the Spire as Ironclad.
Choose one remaining reward action.

HP: {game_state.get('current_hp')}/{game_state.get('max_hp')}
Act: {game_state.get('act')}
Floor: {game_state.get('floor')}
Keys: {format_keys(game_state)}

LEGAL ACTIONS
{chr(10).join(f'{i}: {d}' for i, d in enumerate(descriptions))}

Return ONLY the number.
"""
                selected = self.choose_action(
                    "GENERIC_REWARD_DECISION",
                    prompt,
                    actions,
                    game_state,
                    fallback=0,
                )
                source = "LLM"

            return self.action(
                selected["command"],
                game_state,
                "GENERIC_REWARD_DECISION",
                source,
                legal_actions=[a["description"] for a in actions],
                selected_action=selected["description"],
            )

        if "proceed" in available_commands:
            return self.action(
                "PROCEED",
                game_state,
                "REWARD_COMPLETE",
                "CONTROLLER",
                selected_action="Proceed from reward screen",
            )

        return None

    # --------------------------------------------------------
    # ROUTER
    # --------------------------------------------------------

    def handle_state(self, state):
        available_commands = state.get("available_commands", []) or []
        if not state.get("ready_for_command", False):
            return None

        in_game = state.get("in_game", False)

        # ----------------------------------------------------
        # Transition from an active run back to menu without a
        # GAME_OVER snapshot. Keep this as a fallback only.
        # ----------------------------------------------------
        if not in_game and self.was_in_game:
            if not self.run_end_logged:
                self.finalize_run(
                    self.last_game_state,
                    victory=False,
                    reason="IN_GAME_FALSE_WITHOUT_GAME_OVER",
                )

            self.current_run_id = None
            self.was_in_game = False
            self.start_command_sent = False
            self.reset_for_new_run()

        # ----------------------------------------------------
        # MAIN MENU -> start fresh independent run
        # ----------------------------------------------------
        if not in_game:
            # After exactly MAX_COMPLETED_RUNS completed runs, stay idle at the
            # main menu instead of automatically starting run 31.
            if self.experiment_complete:
                return None

            if "start" not in available_commands:
                return None

            if self.current_run_id is None:
                self.current_run_id = create_run_id()
                self.log_run_event(
                    "RUN_START",
                    character=CHARACTER,
                    ascension=ASCENSION,
                )

            if self.start_command_sent:
                return None

            self.start_command_sent = True
            return self.action(
                f"START {CHARACTER} {ASCENSION}",
                {},
                "START_RUN",
                "CONTROLLER",
                selected_action=f"Start {CHARACTER} Ascension {ASCENSION}",
            )

        # ----------------------------------------------------
        # ACTIVE RUN STATE
        # ----------------------------------------------------
        self.was_in_game = True
        self.start_command_sent = False

        raw_game_state = state.get("game_state", {}) or {}
        self.cache_active_state(raw_game_state)

        # Route/prompt code sees a complete key object even if the installed
        # CommunicationMod build omits it from the wire protocol.
        game_state = dict(raw_game_state)
        game_state["keys"] = self.get_effective_keys(raw_game_state)

        screen_type = str(game_state.get("screen_type", "NONE"))
        screen_state = game_state.get("screen_state", {}) or {}
        choices = game_state.get("choice_list", []) or []
        room_phase = str(game_state.get("room_phase", ""))

        if self.last_screen_type == "GRID" and screen_type != "GRID":
            self.pending_grid_context = None
        self.last_screen_type = screen_type

        # ----------------------------------------------------
        # GAME OVER: log outcome before CommunicationMod clears
        # the dungeon, then press its Proceed button.
        # ----------------------------------------------------
        if screen_type == "GAME_OVER":
            victory = bool(screen_state.get("victory", False))
            score = screen_state.get("score")
            self.finalize_run(
                game_state,
                victory=victory,
                score=score,
                reason="VICTORY" if victory else "DEATH",
            )
            if "proceed" in available_commands:
                return self.action(
                    "PROCEED",
                    game_state,
                    "GAME_OVER_PROCEED",
                    "CONTROLLER",
                    selected_action="Return from game-over screen",
                    metadata={"victory": victory, "score": score},
                )
            return None

        # ----------------------------------------------------
        # COMPLETE is a generic finished-room state in
        # CommunicationMod. It requires no LLM reasoning.
        # ----------------------------------------------------
        if screen_type == "COMPLETE" and "proceed" in available_commands:
            return self.action(
                "PROCEED",
                game_state,
                "COMPLETE_PROCEED",
                "CONTROLLER",
                selected_action="Proceed from completed room",
            )

        # ----------------------------------------------------
        # Optional usable out-of-combat potions. This executes
        # before a strategic screen action, but only when an
        # actual potion reports can_use=true.
        # ----------------------------------------------------
        if screen_type in {"EVENT", "REST", "MAP", "SHOP_SCREEN", "CARD_REWARD", "BOSS_REWARD"}:
            potion_command = self.maybe_use_out_of_combat_potion(
                game_state, available_commands
            )
            if potion_command:
                return potion_command

        # ----------------------------------------------------
        # NEOW
        # ----------------------------------------------------
        if screen_type == "EVENT" and screen_state.get("event_name") == "Neow":
            lowered = lower_list(choices)
            if "talk" in lowered:
                i = lowered.index("talk")
                return self.action(
                    f"CHOOSE {i}",
                    game_state,
                    "NEOW_TALK",
                    "CONTROLLER",
                    legal_actions=choices,
                    selected_action="talk",
                )
            if "leave" in lowered:
                i = lowered.index("leave")
                return self.action(
                    f"CHOOSE {i}",
                    game_state,
                    "NEOW_LEAVE",
                    "CONTROLLER",
                    legal_actions=choices,
                    selected_action="leave",
                )

            actions = self.build_event_actions(game_state)
            if not actions:
                return None
            if len(actions) == 1:
                selected = actions[0]
                source = "CONTROLLER"
            else:
                selected = self.choose_event(game_state, actions)
                source = "LLM"
            self.pending_grid_context = (
                f"Follow-up card selection caused by Neow option: {selected['description']}"
            )
            return self.action(
                selected["command"],
                game_state,
                "NEOW_BLESSING",
                source,
                legal_actions=[a["description"] for a in actions],
                selected_action=selected["description"],
            )

        # ----------------------------------------------------
        # GENERIC EVENT, including Gremlin Wheel and
        # Match-and-Keep. Disabled event buttons are mapped by
        # screen_state.options[].choice_index, not list position.
        # ----------------------------------------------------
        if screen_type == "EVENT" and "choose" in available_commands:
            actions = self.build_event_actions(game_state)
            if not actions:
                return None
            if len(actions) == 1:
                selected = actions[0]
                source = "CONTROLLER"
            else:
                selected = self.choose_event(game_state, actions)
                source = "LLM"

            self.pending_grid_context = (
                f"Follow-up card selection caused by event option: {selected['description']}"
            )
            return self.action(
                selected["command"],
                game_state,
                "EVENT_DECISION",
                source,
                legal_actions=[a["description"] for a in actions],
                selected_action=selected["description"],
            )

        # ----------------------------------------------------
        # CHEST
        # ----------------------------------------------------
        if screen_type == "CHEST":
            lowered = lower_list(choices)
            if "open" in lowered and "choose" in available_commands:
                i = lowered.index("open")
                return self.action(
                    f"CHOOSE {i}",
                    game_state,
                    "CHEST_OPEN",
                    "CONTROLLER",
                    legal_actions=choices,
                    selected_action="Open chest",
                )
            if "proceed" in available_commands:
                return self.action(
                    "PROCEED",
                    game_state,
                    "CHEST_COMPLETE",
                    "CONTROLLER",
                    selected_action="Proceed from chest",
                )
            return None

        # ----------------------------------------------------
        # SHOP ROOM
        # ----------------------------------------------------
        if screen_type == "SHOP_ROOM":
            shop_key = (game_state.get("seed"), game_state.get("floor"))
            lowered = lower_list(choices)
            if (
                shop_key not in self.entered_shop_rooms
                and "shop" in lowered
                and "choose" in available_commands
            ):
                self.entered_shop_rooms.add(shop_key)
                i = lowered.index("shop")
                return self.action(
                    f"CHOOSE {i}",
                    game_state,
                    "ENTER_SHOP",
                    "CONTROLLER",
                    legal_actions=choices,
                    selected_action="Enter merchant",
                    metadata={"shop_key": str(shop_key)},
                )
            if "proceed" in available_commands:
                return self.action(
                    "PROCEED",
                    game_state,
                    "LEAVE_SHOP_ROOM",
                    "CONTROLLER",
                    selected_action="Proceed from merchant room",
                )
            return None

        # ----------------------------------------------------
        # SHOP SCREEN
        # ----------------------------------------------------
        if screen_type == "SHOP_SCREEN":
            actions = self.build_shop_actions(game_state, available_commands)
            if not actions:
                self.dump_full_state("SHOP_SCREEN produced no legal actions", state)
                self.log_run_event(
                    "UNHANDLED_STATE",
                    game_state,
                    reason="SHOP_SCREEN produced no legal actions",
                    available_commands=available_commands,
                    choices=choices,
                )
                return None

            if len(actions) == 1:
                selected = actions[0]
                source = "CONTROLLER"
            else:
                selected = self.choose_shop(game_state, actions)
                source = "LLM"

            if selected.get("kind") == "purge":
                self.pending_grid_context = "Choose one card to remove at the merchant."

            return self.action(
                selected["command"],
                game_state,
                "SHOP_DECISION",
                source,
                legal_actions=[a["description"] for a in actions],
                selected_action=selected["description"],
            )

        # ----------------------------------------------------
        # REST
        # ----------------------------------------------------
        if screen_type == "REST":
            if "proceed" in available_commands and (
                screen_state.get("has_rested", False)
                or not (screen_state.get("rest_options", []) or [])
            ):
                return self.action(
                    "PROCEED",
                    game_state,
                    "REST_COMPLETE",
                    "CONTROLLER",
                    selected_action="Proceed from campfire",
                )

            if choices and "choose" in available_commands:
                if len(choices) == 1:
                    selected = {
                        "command": "CHOOSE 0",
                        "description": choices[0],
                        "choice": choices[0],
                    }
                    source = "CONTROLLER"
                else:
                    selected = self.choose_rest(game_state)
                    source = "LLM"

                choice = str(selected.get("choice", "")).lower()
                if choice == "smith":
                    self.pending_grid_context = "Choose one card to upgrade at the campfire."
                elif choice == "toke":
                    self.pending_grid_context = "Choose one card to remove using Peace Pipe."

                return self.action(
                    selected["command"],
                    game_state,
                    "REST_DECISION",
                    source,
                    legal_actions=choices,
                    selected_action=selected["description"],
                )
            return None

        # ----------------------------------------------------
        # BOSS RELIC REWARD
        # ----------------------------------------------------
        if screen_type == "BOSS_REWARD":
            actions = self.build_boss_reward_actions(game_state, available_commands)
            if not actions:
                return None
            if len(actions) == 1:
                selected = actions[0]
                source = "CONTROLLER"
            else:
                selected = self.choose_boss_reward(game_state, actions)
                source = "LLM"
            return self.action(
                selected["command"],
                game_state,
                "BOSS_REWARD_DECISION",
                source,
                legal_actions=[a["description"] for a in actions],
                selected_action=selected["description"],
                metadata={
                    "boss_relic": (selected.get("relic") or {}).get("name")
                    if selected.get("relic")
                    else None
                },
            )

        # ----------------------------------------------------
        # GRID
        # ----------------------------------------------------
        if screen_type == "GRID":
            selected_cards = screen_state.get("selected_cards", []) or []
            required_cards = screen_state.get("num_cards")
            any_number = bool(screen_state.get("any_number", False))

            # For exact-count GRID screens, once the requested number has been
            # selected, confirming is deterministic and should not consume
            # another LLM call or risk selecting an already-selected card.
            if (
                "confirm" in available_commands
                and not any_number
                and isinstance(required_cards, int)
                and required_cards > 0
                and len(selected_cards) >= required_cards
            ):
                self.last_grid_fingerprint = None
                self.last_grid_command = None
                return self.action(
                    "CONFIRM",
                    game_state,
                    "GRID_CONFIRM",
                    "CONTROLLER",
                    selected_action="Confirm completed GRID selection",
                    metadata={"context": self.pending_grid_context},
                )

            if not choices and "confirm" in available_commands:
                self.last_grid_fingerprint = None
                self.last_grid_command = None
                return self.action(
                    "CONFIRM",
                    game_state,
                    "GRID_CONFIRM",
                    "CONTROLLER",
                    selected_action="Confirm GRID selection",
                    metadata={"context": self.pending_grid_context},
                )

            actions = self.build_grid_actions(game_state, available_commands)
            if not actions:
                return None
            if len(actions) == 1:
                selected = actions[0]
                source = "CONTROLLER"
            else:
                selected = self.choose_grid(game_state, available_commands, actions)
                source = "LLM"
                selected = self.recover_grid_no_progress(game_state, actions, selected)
            return self.action(
                selected["command"],
                game_state,
                "GRID_DECISION",
                source,
                legal_actions=[a["description"] for a in actions],
                selected_action=selected["description"],
                metadata={"context": self.pending_grid_context},
            )

        # ----------------------------------------------------
        # HAND SELECT
        # ----------------------------------------------------
        if screen_type == "HAND_SELECT":
            if not choices and "confirm" in available_commands:
                return self.action(
                    "CONFIRM",
                    game_state,
                    "HAND_SELECT_CONFIRM",
                    "CONTROLLER",
                    selected_action="Finish hand selection",
                )

            actions = self.build_hand_select_actions(game_state, available_commands)
            if not actions:
                return None
            if len(actions) == 1:
                selected = actions[0]
                source = "CONTROLLER"
            else:
                selected = self.choose_hand_select(game_state, actions)
                source = "LLM"
            return self.action(
                selected["command"],
                game_state,
                "HAND_SELECT_DECISION",
                source,
                legal_actions=[a["description"] for a in actions],
                selected_action=selected["description"],
            )

        # ----------------------------------------------------
        # MAP
        # ----------------------------------------------------
        if screen_type == "MAP" and choices and "choose" in available_commands:
            if len(choices) == 1:
                return self.action(
                    f"CHOOSE {choices[0]}",
                    game_state,
                    "MAP_DECISION",
                    "CONTROLLER",
                    legal_actions=choices,
                    selected_action=choices[0],
                )
            selected = self.choose_map(game_state)
            return self.action(
                selected["command"],
                game_state,
                "MAP_DECISION",
                "LLM",
                legal_actions=[a for a in choices],
                selected_action=selected["description"],
            )

        # ----------------------------------------------------
        # COMBAT. Potion commands are part of the same legal
        # action space as PLAY and END.
        # ----------------------------------------------------
        if room_phase == "COMBAT" and game_state.get("combat_state") and (
            "play" in available_commands
            or "end" in available_commands
            or "potion" in available_commands
        ):
            actions = self.build_combat_actions(game_state, available_commands)
            if not actions:
                self.dump_full_state("Combat produced no legal actions", state)
                self.log_run_event(
                    "UNHANDLED_STATE",
                    game_state,
                    reason="Combat produced no legal actions",
                    available_commands=available_commands,
                )
                return None

            if len(actions) == 1:
                selected = actions[0]
                source = "CONTROLLER"
            else:
                selected = self.choose_combat(game_state, actions)
                source = "LLM"
            return self.action(
                selected["command"],
                game_state,
                "COMBAT_DECISION",
                source,
                legal_actions=[a["description"] for a in actions],
                selected_action=selected["description"],
            )

        # ----------------------------------------------------
        # COMBAT/CHEST REWARD
        # ----------------------------------------------------
        if screen_type == "COMBAT_REWARD":
            return self.handle_combat_reward(game_state, available_commands)

        # ----------------------------------------------------
        # CARD REWARD
        # ----------------------------------------------------
        if screen_type == "CARD_REWARD":
            actions = self.build_card_reward_actions(game_state, available_commands)
            if not actions:
                return None
            if len(actions) == 1:
                selected = actions[0]
                source = "CONTROLLER"
            else:
                selected = self.choose_card_reward(game_state, actions)
                source = "LLM"
            return self.action(
                selected["command"],
                game_state,
                "CARD_REWARD_DECISION",
                source,
                legal_actions=[a["description"] for a in actions],
                selected_action=selected["description"],
            )

        # ----------------------------------------------------
        # NONE outside combat is often a transient action-manager
        # state. Do not falsely classify it as a controller gap.
        # ----------------------------------------------------
        if screen_type == "NONE":
            self.log_run_event(
                "TRANSIENT_STATE",
                game_state,
                available_commands=available_commands,
            )
            return None

        # ----------------------------------------------------
        # Anything else is a genuine structural surprise.
        # ----------------------------------------------------
        self.log_debug("")
        self.log_debug("=== UNHANDLED STATE ===")
        self.log_debug(f"Screen type: {screen_type}")
        self.log_debug(f"Room phase: {room_phase}")
        self.log_debug(f"Available commands: {available_commands}")
        self.log_debug(f"Choices: {choices}")
        self.log_debug(f"Screen state: {screen_state}")

        self.dump_full_state("UNHANDLED_STATE", state)
        self.log_run_event(
            "UNHANDLED_STATE",
            game_state,
            available_commands=available_commands,
            choices=choices,
            screen_state=screen_state,
        )
        return None


# ============================================================
# COMMUNICATIONMOD ENTRY POINT
# ============================================================

def _stdin_reader(line_queue):
    """Read CommunicationMod stdout asynchronously so the main loop can watchdog stalls."""
    try:
        for line in sys.stdin:
            line_queue.put(line)
    finally:
        line_queue.put(None)


def main():
    agent = STSAgent(use_llm=True, enable_logging=True)

    # CommunicationMod handshake. Nothing except commands may be printed to stdout.
    print("ready", flush=True)

    agent.log_debug("")
    agent.log_debug("========================================")
    agent.log_debug(f"STS GPT AGENT STARTED — {AGENT_VERSION}")
    agent.log_debug(
        f"Baseline progress: {agent.completed_run_count}/{MAX_COMPLETED_RUNS} completed runs"
    )
    if agent.experiment_complete:
        agent.log_debug("Baseline batch already complete; no new run will be started.")
    agent.log_debug("========================================")

    line_queue = queue.Queue()
    reader = threading.Thread(
        target=_stdin_reader,
        args=(line_queue,),
        daemon=True,
        name="communicationmod-stdin-reader",
    )
    reader.start()

    waiting_for_state_after_command = False
    watchdog_requests = 0

    while True:
        try:
            if waiting_for_state_after_command:
                line = line_queue.get(timeout=STATE_RESPONSE_TIMEOUT_SECONDS)
            else:
                line = line_queue.get()
        except queue.Empty:
            # A command was issued but CommunicationMod did not send a new
            # state. STATE is documented as always available and is safe for
            # resynchronizing the protocol.
            watchdog_requests += 1
            agent.log_debug(
                f"STATE_WATCHDOG: no state received for "
                f"{STATE_RESPONSE_TIMEOUT_SECONDS:.0f}s after a command; "
                f"requesting STATE ({watchdog_requests}/{WATCHDOG_STATE_REQUEST_LIMIT})."
            )
            agent.log_run_event(
                "STATE_WATCHDOG",
                agent.last_game_state or {},
                watchdog_request=watchdog_requests,
                timeout_seconds=STATE_RESPONSE_TIMEOUT_SECONDS,
            )
            print("STATE", flush=True)
            waiting_for_state_after_command = True

            if watchdog_requests >= WATCHDOG_STATE_REQUEST_LIMIT:
                # Keep trying at a bounded cadence rather than silently dying.
                time.sleep(WATCHDOG_RETRY_DELAY_SECONDS)
            continue

        if line is None:
            agent.log_debug("STDIN_EOF: CommunicationMod closed the external-process pipe.")
            agent.log_run_event(
                "STDIN_EOF",
                agent.last_game_state or {},
                message="CommunicationMod closed stdin for the agent process.",
            )
            break

        waiting_for_state_after_command = False
        watchdog_requests = 0

        try:
            state = json.loads(line)

            # CommunicationMod reports invalid commands as a top-level error
            # object and then waits for the next command. The old controller
            # treated this like a normal state, returned None, and deadlocked.
            if isinstance(state, dict) and state.get("error"):
                error_message = str(state.get("error"))
                agent.log_debug(f"COMMUNICATIONMOD_ERROR: {error_message}")
                agent.log_run_event(
                    "COMMUNICATIONMOD_ERROR",
                    agent.last_game_state or {},
                    error_message=error_message,
                    raw_response=state,
                )
                print("STATE", flush=True)
                waiting_for_state_after_command = True
                continue

            agent.log_state_summary(state)

            command = agent.handle_state(state)
            if command:
                if COMMAND_DELAY_SECONDS > 0:
                    time.sleep(COMMAND_DELAY_SECONDS)
                print(command, flush=True)
                waiting_for_state_after_command = True
                continue

            # If CommunicationMod explicitly says it is ready for a command,
            # returning nothing is itself a protocol deadlock. For active runs,
            # WAIT lets transient animations/actions progress; STATE is the
            # universal fallback. Do not do this when the 30-run experiment has
            # intentionally completed and is idling at the menu.
            if (
                isinstance(state, dict)
                and state.get("ready_for_command", False)
                and not (agent.experiment_complete and not state.get("in_game", False))
            ):
                available = state.get("available_commands", []) or []
                recovery_command = (
                    "WAIT 30"
                    if state.get("in_game", False) and "wait" in available
                    else "STATE"
                )
                agent.log_debug(
                    f"NO_COMMAND_RECOVERY: router returned no command while "
                    f"CommunicationMod was ready; sending {recovery_command}."
                )
                agent.log_run_event(
                    "NO_COMMAND_RECOVERY",
                    state.get("game_state", {}) or agent.last_game_state or {},
                    available_commands=available,
                    recovery_command=recovery_command,
                )
                print(recovery_command, flush=True)
                waiting_for_state_after_command = True

        except Exception as exc:
            agent.log_debug("")
            agent.log_debug("========================================")
            agent.log_debug("ERROR")
            agent.log_debug("========================================")
            agent.log_debug(f"{type(exc).__name__}: {exc}")

            try:
                error_game_state = state.get("game_state", {}) or {}
            except Exception:
                error_game_state = {}

            try:
                agent.dump_full_state("ERROR", state)
            except Exception:
                pass

            agent.log_run_event(
                "ERROR",
                error_game_state,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

            # Do not leave CommunicationMod waiting after an unexpected Python
            # exception. STATE is always available and gives us a clean point
            # from which to route again.
            print("STATE", flush=True)
            waiting_for_state_after_command = True


if __name__ == "__main__":
    main()
