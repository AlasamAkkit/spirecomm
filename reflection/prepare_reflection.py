import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RUN_EVENTS_FILE = Path("run_events.jsonl")
STS_MESSAGES_FILE = Path("sts_messages.log")
OUTPUT_DIR = Path("outputs")

# A state summary is written before the LLM call, while the ACTION event is
# written after the LLM returns. Allow a reasonably wide matching window.
MAX_STATE_MATCH_AGE_SECONDS = 120


def parse_timestamp(value):
    if not value:
        return None

    try:
        # Python's fromisoformat accepts offsets. Convert a trailing Z for
        # compatibility with older Python versions.
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        dt = datetime.fromisoformat(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt
    except (TypeError, ValueError):
        return None


def load_jsonl(path, *, tolerate_bad_lines=False):
    rows = []

    if not path.exists():
        return rows

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                if tolerate_bad_lines:
                    continue

                raise ValueError(
                    f"Invalid JSON in {path} on line {line_number}"
                )

    return rows


def load_events():
    return load_jsonl(
        RUN_EVENTS_FILE,
        tolerate_bad_lines=False,
    )


def load_state_summaries():
    # sts_messages.log is expected to contain compact JSON state summaries.
    # Be tolerant in case an old/non-JSON diagnostic line is mixed in.
    return load_jsonl(
        STS_MESSAGES_FILE,
        tolerate_bad_lines=True,
    )


def get_run(events, completed_run_number):
    run_end = None

    for event in events:
        if (
            event.get("event_type") == "RUN_END"
            and event.get("completed_run_number") == completed_run_number
        ):
            run_end = event
            break

    if run_end is None:
        raise ValueError(
            f"Could not find completed run {completed_run_number}"
        )

    run_id = run_end["run_id"]

    run_events = [
        event
        for event in events
        if event.get("run_id") == run_id
    ]

    run_events.sort(
        key=lambda event: parse_timestamp(event.get("timestamp"))
        or datetime.min.replace(tzinfo=timezone.utc)
    )

    return run_events, run_end


def get_run_time_window(run_events):
    timestamps = [
        parse_timestamp(event.get("timestamp"))
        for event in run_events
    ]

    timestamps = [
        timestamp
        for timestamp in timestamps
        if timestamp is not None
    ]

    if not timestamps:
        return None, None

    return min(timestamps), max(timestamps)


def get_run_seed(run_events):
    for event in run_events:
        seed = event.get("seed")

        if seed is not None:
            return seed

    return None


def select_run_state_summaries(
    all_state_summaries,
    run_events,
):
    start_time, end_time = get_run_time_window(run_events)
    run_seed = get_run_seed(run_events)

    if start_time is None or end_time is None:
        return []

    selected = []

    for state in all_state_summaries:
        timestamp = parse_timestamp(state.get("timestamp"))

        if timestamp is None:
            continue

        if not (start_time <= timestamp <= end_time):
            continue

        state_seed = state.get("seed")

        # The menu/startup states can have no seed. Once a seed exists,
        # avoid mixing summaries from a different run.
        if (
            run_seed is not None
            and state_seed is not None
            and state_seed != run_seed
        ):
            continue

        selected.append(state)

    selected.sort(
        key=lambda state: parse_timestamp(state.get("timestamp"))
        or datetime.min.replace(tzinfo=timezone.utc)
    )

    return selected


def format_legal_actions(actions):
    if not actions:
        return ""

    return " | ".join(str(action) for action in actions)


def format_keys(keys):
    if not isinstance(keys, dict):
        return "unknown"

    return (
        f"ruby={bool(keys.get('ruby'))}, "
        f"emerald={bool(keys.get('emerald'))}, "
        f"sapphire={bool(keys.get('sapphire'))}"
    )


def format_monsters(monsters):
    if not monsters:
        return "None"

    parts = []

    for monster in monsters:
        name = monster.get("name", "Unknown")
        hp = monster.get("hp")
        max_hp = monster.get("max_hp")
        block = monster.get("block")
        intent = monster.get("intent")

        parts.append(
            f"{name} "
            f"HP {hp}/{max_hp}, "
            f"Block {block}, "
            f"Intent {intent}"
        )

    return " | ".join(parts)


def find_nearest_state_before(
    event,
    state_summaries,
    *,
    require_combat=False,
):
    """
    Match an ACTION event to the latest compact state summary that came before
    it on the same Act/floor.

    ACTION is logged after the LLM response, so the corresponding state can be
    several seconds earlier.
    """
    event_time = parse_timestamp(event.get("timestamp"))

    if event_time is None:
        return None

    event_act = event.get("act")
    event_floor = event.get("floor")
    event_seed = event.get("seed")
    event_screen_type = event.get("screen_type")

    candidates = []

    for state in state_summaries:
        state_time = parse_timestamp(state.get("timestamp"))

        if state_time is None or state_time > event_time:
            continue

        age_seconds = (event_time - state_time).total_seconds()

        if age_seconds > MAX_STATE_MATCH_AGE_SECONDS:
            continue

        if state.get("act") != event_act:
            continue

        if state.get("floor") != event_floor:
            continue

        if (
            event_seed is not None
            and state.get("seed") is not None
            and state.get("seed") != event_seed
        ):
            continue

        if require_combat and not state.get("combat"):
            continue

        candidates.append(state)

    if not candidates:
        return None

    # Prefer the closest state with the same screen type when that is useful.
    exact_screen = [
        state
        for state in candidates
        if (
            event_screen_type
            and state.get("screen_type") == event_screen_type
        )
    ]

    pool = exact_screen or candidates

    return max(
        pool,
        key=lambda state: parse_timestamp(state.get("timestamp")),
    )


def is_combat_generated_card_choice(event):
    """
    CARD_REWARD can also be used inside combat for generated-card effects such
    as Skill Potion. Those are not permanent deck-building rewards.
    """
    return (
        event.get("decision_type") == "CARD_REWARD_DECISION"
        and event.get("room_phase") == "COMBAT"
    )


def is_combat_related_action(event):
    decision_type = event.get("decision_type")

    if decision_type in {
        "COMBAT_DECISION",
        "HAND_SELECT_DECISION",
    }:
        return True

    return is_combat_generated_card_choice(event)


def build_follow_up_grid_map(llm_actions):
    """
    Associate a GRID decision with the immediately preceding non-GRID LLM
    decision on the same floor when possible.

    This makes entries such as Smith -> Select Burning Pact easier to read.
    """
    follow_ups = {}
    previous_non_grid = None

    for event in llm_actions:
        decision_type = event.get("decision_type")

        if decision_type == "GRID_DECISION":
            if (
                previous_non_grid is not None
                and previous_non_grid.get("act") == event.get("act")
                and previous_non_grid.get("floor") == event.get("floor")
            ):
                key = previous_non_grid.get("timestamp")
                follow_ups.setdefault(key, []).append(event)

            continue

        previous_non_grid = event

    return follow_ups


def build_compact_trajectory(
    run_events,
    run_end,
    state_summaries,
):
    lines = []

    # ========================================================
    # Outcome
    # ========================================================

    lines.append("# RUN OUTCOME")
    lines.append(f"Result: {run_end.get('result')}")
    lines.append(f"Act reached: {run_end.get('act')}")
    lines.append(f"Floor reached: {run_end.get('floor')}")
    lines.append(f"Score: {run_end.get('score')}")
    lines.append(f"Death reason: {run_end.get('end_reason')}")
    lines.append(f"Boss: {run_end.get('act_boss')}")
    lines.append(
        f"Final keys: {format_keys(run_end.get('final_keys'))}"
    )

    enemies = run_end.get("enemies", [])

    if enemies:
        enemy_text = ", ".join(
            f"{enemy.get('name')} "
            f"({enemy.get('current_hp')}/{enemy.get('max_hp')} HP)"
            for enemy in enemies
        )

        lines.append(f"Final enemies: {enemy_text}")

    lines.append("")

    # ========================================================
    # Final build
    # ========================================================

    lines.append("# FINAL BUILD")

    final_deck = run_end.get("final_deck", []) or []
    final_relics = run_end.get("final_relics", []) or []
    final_potions = run_end.get("final_potions", []) or []

    lines.append(
        f"Deck ({len(final_deck)} cards): "
        + (", ".join(final_deck) if final_deck else "None")
    )

    lines.append(
        "Relics: "
        + (", ".join(final_relics) if final_relics else "None")
    )

    lines.append(
        "Potions: "
        + (", ".join(final_potions) if final_potions else "None")
    )

    lines.append("")

    # ========================================================
    # LLM decisions
    # ========================================================

    llm_actions = [
        event
        for event in run_events
        if (
            event.get("event_type") == "ACTION"
            and event.get("decision_source") == "LLM"
        )
    ]

    follow_up_grids = build_follow_up_grid_map(llm_actions)

    final_floor = run_end.get("floor")
    final_act = run_end.get("act")

    lines.append("# STRATEGIC DECISIONS")
    lines.append(
        "Only non-combat strategic decisions are shown here. "
        "CARD_REWARD states that occurred during combat are treated as "
        "temporary/generated-card choices, not permanent deck rewards."
    )
    lines.append("")

    combat_by_floor = {}

    for event in llm_actions:
        if is_combat_related_action(event):
            key = (
                event.get("act"),
                event.get("floor")
            )

            combat_by_floor.setdefault(key, []).append(event)
            continue

        decision_type = event.get("decision_type")

        # GRID selections are generally subordinate to the decision that opened
        # them. They are printed as follow-ups below the parent where possible.
        if decision_type == "GRID_DECISION":
            continue

        act = event.get("act")
        floor = event.get("floor")
        hp = event.get("current_hp")
        max_hp = event.get("max_hp")
        gold = event.get("gold")
        boss = event.get("act_boss")
        keys = event.get("keys")

        lines.append(
            f"Act {act} Floor {floor} | "
            f"HP {hp}/{max_hp} | "
            f"Gold {gold} | "
            f"{decision_type}"
        )

        if boss:
            lines.append(f"  Act boss: {boss}")

        if isinstance(keys, dict):
            lines.append(f"  Keys: {format_keys(keys)}")

        lines.append(
            f"  Chosen: {event.get('selected_action')}"
        )

        legal = event.get("legal_actions")

        if legal:
            lines.append(
                f"  Alternatives: {format_legal_actions(legal)}"
            )

        for grid_event in follow_up_grids.get(
            event.get("timestamp"),
            [],
        ):
            lines.append(
                "  Follow-up selection: "
                f"{grid_event.get('selected_action')}"
            )

        # Important data-quality note: the baseline ACTION logger did not store
        # map topology, so do not pretend x-coordinates identify room types.
        if decision_type == "MAP_DECISION":
            lines.append(
                "  Context note: baseline ACTION logs do not contain the "
                "full map topology/node symbols for this decision."
            )

        lines.append("")

    # ========================================================
    # Combat summaries
    # ========================================================

    lines.append("# COMBAT SUMMARY")

    for (act, floor), actions in sorted(
        combat_by_floor.items(),
        key=lambda item: item[0]
    ):
        combat_actions = [
            event
            for event in actions
            if event.get("decision_type") in {
                "COMBAT_DECISION",
                "HAND_SELECT_DECISION",
            }
        ]

        if combat_actions:
            first = combat_actions[0]
            last = combat_actions[-1]

            line = (
                f"Act {act} Floor {floor}: "
                f"{len(combat_actions)} LLM combat decisions, "
                f"first logged HP "
                f"{first.get('current_hp')}/{first.get('max_hp')}, "
                f"last logged HP "
                f"{last.get('current_hp')}/{last.get('max_hp')}"
            )
        else:
            line = (
                f"Act {act} Floor {floor}: "
                "generated-card choice recorded during combat"
            )

        lines.append(line)

        selected = []

        for event in actions:
            if is_combat_generated_card_choice(event):
                selected.append(
                    "Choose temporary/generated card: "
                    + str(event.get("selected_action"))
                )
            else:
                selected.append(
                    str(event.get("selected_action"))
                )

        if len(selected) <= 8:
            sample = selected
        else:
            sample = (
                selected[:4]
                + ["..."]
                + selected[-4:]
            )

        lines.append(
            "  Actions: "
            + " -> ".join(sample)
        )

        # Give one compact snapshot of who was being fought where available.
        representative = None

        for event in actions:
            representative = find_nearest_state_before(
                event,
                state_summaries,
                require_combat=True,
            )

            if representative:
                break

        if representative:
            combat = representative.get("combat") or {}
            lines.append(
                "  Combat context: "
                + format_monsters(combat.get("monsters", []))
            )

    lines.append("")

    # ========================================================
    # Detailed final combat
    # ========================================================

    final_combat_actions = [
        event
        for event in llm_actions
        if (
            event.get("floor") == final_floor
            and event.get("act") == final_act
            and is_combat_related_action(event)
        )
    ]

    lines.append("# FINAL COMBAT DETAILS")
    lines.append(
        "The compact state log is matched by timestamp to recover the combat "
        "turn, energy, player block, hand, and monster HP/block/intent that "
        "were available near each decision."
    )
    lines.append("")

    for event in final_combat_actions[-12:]:
        state = find_nearest_state_before(
            event,
            state_summaries,
            require_combat=True,
        )

        if state:
            combat = state.get("combat") or {}

            lines.append(
                f"Turn {combat.get('turn')} | "
                f"HP {event.get('current_hp')}/"
                f"{event.get('max_hp')} | "
                f"Block {combat.get('block')} | "
                f"Energy {combat.get('energy')} | "
                f"{event.get('decision_type')}"
            )

            hand = combat.get("hand", []) or []

            if hand:
                lines.append(
                    "  Hand: "
                    + ", ".join(str(card) for card in hand)
                )

            lines.append(
                "  Enemies: "
                + format_monsters(combat.get("monsters", []))
            )
        else:
            lines.append(
                f"HP {event.get('current_hp')}/"
                f"{event.get('max_hp')} | "
                f"{event.get('decision_type')} | "
                "No matching compact combat state found"
            )

        if is_combat_generated_card_choice(event):
            lines.append(
                "  Context: temporary/generated card choice during combat"
            )

        lines.append(
            f"  Chosen: {event.get('selected_action')}"
        )

        legal = event.get("legal_actions")

        if legal:
            lines.append(
                "  Alternatives: "
                f"{format_legal_actions(legal)}"
            )

        lines.append("")

    # ========================================================
    # Data limitations
    # ========================================================

    lines.append("# DATA LIMITATIONS")
    lines.append(
        "- The baseline ACTION events store HP, gold, boss, keys, legal "
        "actions and the selected action, but not a full deck/relic/potion "
        "snapshot at every decision."
    )
    lines.append(
        "- sts_messages.log stores compact combat state including turn, "
        "energy, player block, hand and monster HP/block/intent, but not the "
        "full map topology or card-effect text."
    )
    lines.append(
        "- Therefore the reflector must not infer unavailable route node types, "
        "exact incoming damage, or per-decision deck/relic state unless it is "
        "explicitly present elsewhere in this trajectory."
    )
    lines.append(
        "- CARD_REWARD decisions with room_phase=COMBAT are temporary/generated "
        "card choices (for example potion-generated cards) and must not be "
        "treated as permanent deck additions."
    )

    return "\n".join(lines)


def main():
    if len(sys.argv) != 2:
        print("Usage: python prepare_reflection.py <run_number>")
        return

    try:
        run_number = int(sys.argv[1])
    except ValueError:
        print("Run number must be an integer.")
        return

    events = load_events()

    run_events, run_end = get_run(
        events,
        run_number
    )

    all_state_summaries = load_state_summaries()

    run_state_summaries = select_run_state_summaries(
        all_state_summaries,
        run_events,
    )

    OUTPUT_DIR.mkdir(exist_ok=True)

    raw_output_file = (
        OUTPUT_DIR
        / f"run_{run_number:02d}_raw.json"
    )

    with raw_output_file.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            run_events,
            f,
            indent=2,
            ensure_ascii=False
        )

    state_output_file = (
        OUTPUT_DIR
        / f"run_{run_number:02d}_states.json"
    )

    with state_output_file.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            run_state_summaries,
            f,
            indent=2,
            ensure_ascii=False
        )

    trajectory = build_compact_trajectory(
        run_events,
        run_end,
        run_state_summaries,
    )

    trajectory_file = (
        OUTPUT_DIR
        / f"run_{run_number:02d}_trajectory_v2.txt"
    )

    trajectory_file.write_text(
        trajectory,
        encoding="utf-8"
    )

    print(f"Run {run_number}")
    print(f"Run ID: {run_end['run_id']}")
    print(f"Result: {run_end.get('result')}")
    print(f"Act: {run_end.get('act')}")
    print(f"Floor: {run_end.get('floor')}")
    print(f"Score: {run_end.get('score')}")
    print(f"Raw events saved: {raw_output_file}")
    print(
        f"Matched state summaries: "
        f"{len(run_state_summaries)}"
    )
    print(f"State summaries saved: {state_output_file}")
    print(f"Trajectory saved: {trajectory_file}")

    if not STS_MESSAGES_FILE.exists():
        print(
            "WARNING: sts_messages.log was not found. "
            "The trajectory was generated without enriched combat context."
        )
    elif not run_state_summaries:
        print(
            "WARNING: sts_messages.log was found, but no state summaries "
            "matched this run. Check that it belongs to the same baseline batch."
        )


if __name__ == "__main__":
    main()
