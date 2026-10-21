from __future__ import annotations

import json
import shutil
from pathlib import Path

CHECKPOINT_RUN = 32
EXPECTED_RUN32_CONTROLLER = "c2-continual-teaching-v1.1.1-card-prior-turn-planner"
NEXT_CONTROLLER = "c2-continual-teaching-v1.2.0-persistent-planning"

# Archived helper: resolve the live project paths from this nested location.
BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BASE_DIR.parent
REFLECTION_DIR = PROJECT_DIR / "reflection"
ARCHIVE_DIR = BASE_DIR / "runs" / "C2_continual_through_run32_pre_v1_2"

EVENTS_FILE = BASE_DIR / "run_events_c2.jsonl"
MEMORY_FILE = REFLECTION_DIR / "condition_c2_raw_memory.jsonl"
PLAYBOOK_FILE = REFLECTION_DIR / "condition_c2_playbook.json"
FEEDBACK_FILE = REFLECTION_DIR / "condition_c2_feedback.jsonl"
OUTPUT_DIR = REFLECTION_DIR / "condition_c2_outputs"
SEED_FILE = BASE_DIR / "c2_continual_seed_schedule.json"
PROGRESS_FILE = BASE_DIR / "c2_continual_progress.json"

CONTROLLERS = [
    BASE_DIR / "test_connection_c2_continual_v1.py",
    BASE_DIR / "test_connection_c2_continual_v1_1.py",
    BASE_DIR / "test_connection_c2_continual_v1_1_1.py",
    BASE_DIR / "test_connection_c2_continual_v1_1_2.py",
]


def read_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path} line {line_number}") from exc
    return rows


def main():
    required = [
        EVENTS_FILE,
        MEMORY_FILE,
        PLAYBOOK_FILE,
        FEEDBACK_FILE,
        OUTPUT_DIR,
        SEED_FILE,
        PROGRESS_FILE,
        *CONTROLLERS[:3],
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing Run-32 checkpoint file(s):\n- " + "\n- ".join(missing))

    events = read_jsonl(EVENTS_FILE)
    run_ends = {
        e.get("completed_run_number"): e
        for e in events
        if e.get("event_type") == "RUN_END"
        and isinstance(e.get("completed_run_number"), int)
    }
    reflections = {
        e.get("completed_run_number"): e
        for e in events
        if e.get("event_type") == "POST_RUN_REFLECTION_COMPLETE"
        and isinstance(e.get("completed_run_number"), int)
    }

    expected = set(range(1, CHECKPOINT_RUN + 1))
    if set(run_ends) != expected:
        raise ValueError(
            f"Expected RUN_END records 1-{CHECKPOINT_RUN}; found {sorted(run_ends)}"
        )
    if set(reflections) != expected:
        raise ValueError(
            f"Expected reflected runs 1-{CHECKPOINT_RUN}; found {sorted(reflections)}"
        )

    run32 = run_ends[CHECKPOINT_RUN]
    if run32.get("continual_controller_version") != EXPECTED_RUN32_CONTROLLER:
        raise ValueError(
            "Run 32 controller does not match the recorded pre-v1.2 architecture: "
            f"{run32.get('continual_controller_version')!r}"
        )

    memory = read_jsonl(MEMORY_FILE)
    memory_by_id = {item.get("id"): item for item in memory}
    if len(memory_by_id) != len(memory):
        raise ValueError("Duplicate raw-memory ID detected.")

    playbook = json.loads(PLAYBOOK_FILE.read_text(encoding="utf-8"))
    if int(playbook.get("updated_through_run") or 0) != CHECKPOINT_RUN:
        raise ValueError(
            f"Playbook updated_through_run={playbook.get('updated_through_run')}; "
            f"expected {CHECKPOINT_RUN}."
        )

    rules = [
        rule
        for rows in (playbook.get("categories", {}) or {}).values()
        for rule in (rows or [])
    ]
    covered = {
        memory_id
        for rule in rules
        for memory_id in (rule.get("source_memory_ids") or [])
    }
    missing_coverage = sorted(set(memory_by_id) - covered)
    if missing_coverage:
        raise ValueError(
            "Playbook dropped raw-memory coverage: " + ", ".join(missing_coverage)
        )

    feedback_rows = read_jsonl(FEEDBACK_FILE)
    if len(feedback_rows) < CHECKPOINT_RUN:
        raise ValueError(
            f"Feedback bank has only {len(feedback_rows)} rows; expected at least {CHECKPOINT_RUN}."
        )

    run32_review = OUTPUT_DIR / "run_32_feedback_review.json"
    run32_final = OUTPUT_DIR / "run_32_final_reflection.json"
    if not run32_review.exists() or not run32_final.exists():
        raise ValueError("Run 32 feedback/final-reflection artifacts are incomplete.")

    review = json.loads(run32_review.read_text(encoding="utf-8"))
    if str(review.get("status", "")).upper() == "PENDING":
        raise ValueError("Run 32 feedback review is still PENDING.")

    if ARCHIVE_DIR.exists():
        shutil.rmtree(ARCHIVE_DIR)
    ARCHIVE_DIR.mkdir(parents=True)

    copies = {
        EVENTS_FILE: "run_events_c2.jsonl",
        MEMORY_FILE: "condition_c2_raw_memory.jsonl",
        PLAYBOOK_FILE: "condition_c2_playbook.json",
        FEEDBACK_FILE: "condition_c2_feedback.jsonl",
        SEED_FILE: "c2_continual_seed_schedule.json",
        PROGRESS_FILE: "c2_continual_progress.json",
    }
    for controller in CONTROLLERS:
        if controller.exists():
            copies[controller] = controller.name

    for source, name in copies.items():
        shutil.copy2(source, ARCHIVE_DIR / name)

    shutil.copytree(OUTPUT_DIR, ARCHIVE_DIR / "condition_c2_outputs")

    for optional in [
        BASE_DIR / "agent_debug_c2.log",
        BASE_DIR / "sts_messages_c2.log",
        BASE_DIR / "state_dumps_c2.jsonl",
    ]:
        if optional.exists():
            shutil.copy2(optional, ARCHIVE_DIR / optional.name)

    summary = {
        "schema": "c2-continual-checkpoint-v1",
        "checkpoint_run": CHECKPOINT_RUN,
        "controller_version": EXPECTED_RUN32_CONTROLLER,
        "run_32_result": run32.get("result"),
        "run_32_floor": run32.get("floor"),
        "run_32_score": run32.get("score"),
        "run_32_ascension": run32.get("active_ascension"),
        "raw_memory_count": len(memory),
        "playbook_rule_count": len(rules),
        "playbook_updated_through_run": playbook.get("updated_through_run"),
        "feedback_row_count": len(feedback_rows),
        "next_run": CHECKPOINT_RUN + 1,
        "next_controller": NEXT_CONTROLLER,
        "research_note": (
            "Runs 29-32 exposed local card-reward reasoning, turn-plan inconsistency, "
            "and prompt growth from cumulative memory; Run 33 begins the persistent-planning intervention."
        ),
    }
    (ARCHIVE_DIR / "CHECKPOINT_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("C2 continual Run-32 checkpoint validation: PASS")
    print(f"Completed/reflected runs: {CHECKPOINT_RUN}")
    print(f"Raw lessons: {len(memory)}")
    print(f"Playbook rules: {len(rules)}")
    print(f"Playbook updated through: {playbook.get('updated_through_run')}")
    print(f"Feedback rows: {len(feedback_rows)}")
    print(f"Checkpoint copied to: {ARCHIVE_DIR}")
    print("Next run: 33")
    print(f"Next controller: {NEXT_CONTROLLER}")


if __name__ == "__main__":
    main()
