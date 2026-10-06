from __future__ import annotations

import json
import shutil
from pathlib import Path

CHECKPOINT_RUNS = 15
EXPECTED_RAW_LESSONS = 25
EXPECTED_PLAYBOOK_RULES = 17

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
REFLECTION_DIR = PROJECT_DIR / "reflection"
ARCHIVE_DIR = BASE_DIR / "runs" / "C2_v1_2_1_15runs_final"

EVENTS_FILE = BASE_DIR / "run_events_c2.jsonl"
MEMORY_FILE = REFLECTION_DIR / "condition_c2_raw_memory.jsonl"
PLAYBOOK_FILE = REFLECTION_DIR / "condition_c2_playbook.json"
FEEDBACK_FILE = REFLECTION_DIR / "condition_c2_feedback.jsonl"
OUTPUT_DIR = REFLECTION_DIR / "condition_c2_outputs"

PROGRESS_FILE = BASE_DIR / "c2_continual_progress.json"
SEED_FILE = BASE_DIR / "c2_continual_seed_schedule.json"


def load_jsonl(path: Path):
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
    required = [EVENTS_FILE, MEMORY_FILE, PLAYBOOK_FILE, FEEDBACK_FILE]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing required final C2 working-state file(s):\n- "
            + "\n- ".join(missing)
        )

    events = load_jsonl(EVENTS_FILE)
    run_ends = [e for e in events if e.get("event_type") == "RUN_END"]
    run_numbers = sorted(
        e.get("completed_run_number")
        for e in run_ends
        if isinstance(e.get("completed_run_number"), int)
    )

    if run_numbers != list(range(1, CHECKPOINT_RUNS + 1)):
        raise ValueError(
            "Expected exactly the frozen C2 Run-1..15 event history before "
            f"starting continual teaching; found completed runs {run_numbers}."
        )

    memory = load_jsonl(MEMORY_FILE)
    if len(memory) != EXPECTED_RAW_LESSONS:
        raise ValueError(
            f"Expected {EXPECTED_RAW_LESSONS} final C2 raw lessons, found {len(memory)}."
        )

    ids = [row.get("id") for row in memory]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate raw-memory IDs found in final C2 checkpoint.")

    playbook = json.loads(PLAYBOOK_FILE.read_text(encoding="utf-8"))
    rule_count = sum(
        len(rows or []) for rows in (playbook.get("categories", {}) or {}).values()
    )
    if rule_count != EXPECTED_PLAYBOOK_RULES:
        raise ValueError(
            f"Expected {EXPECTED_PLAYBOOK_RULES} final C2 playbook rules, found {rule_count}."
        )
    if int(playbook.get("updated_through_run") or 0) != CHECKPOINT_RUNS:
        raise ValueError(
            "Final C2 playbook is not updated through Run 15: "
            f"{playbook.get('updated_through_run')}"
        )

    covered = {
        mid
        for rules in (playbook.get("categories", {}) or {}).values()
        for rule in (rules or [])
        for mid in (rule.get("source_memory_ids") or [])
    }
    missing_coverage = sorted(set(ids) - covered)
    if missing_coverage:
        raise ValueError(
            "Final C2 playbook is missing raw-memory coverage for: "
            + ", ".join(missing_coverage)
        )

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(EVENTS_FILE, ARCHIVE_DIR / "run_events_c2.jsonl")
    shutil.copy2(MEMORY_FILE, ARCHIVE_DIR / "condition_c2_raw_memory.jsonl")
    shutil.copy2(PLAYBOOK_FILE, ARCHIVE_DIR / "condition_c2_playbook.json")
    shutil.copy2(FEEDBACK_FILE, ARCHIVE_DIR / "condition_c2_feedback.jsonl")

    if OUTPUT_DIR.exists():
        archive_outputs = ARCHIVE_DIR / "condition_c2_outputs"
        shutil.copytree(OUTPUT_DIR, archive_outputs, dirs_exist_ok=True)

    if PROGRESS_FILE.exists():
        raise ValueError(
            f"{PROGRESS_FILE} already exists. Continual teaching may already have been initialized; "
            "inspect the current state rather than resetting progression."
        )
    if SEED_FILE.exists():
        raise ValueError(
            f"{SEED_FILE} already exists. Continual teaching may already have generated new seeds; "
            "do not reset it silently."
        )

    progress = {
        "schema": "c2-continual-progress-v1",
        "checkpoint_completed_runs": CHECKPOINT_RUNS,
        "current_ascension": 0,
        "highest_cleared_ascension": -1,
        "processed_run_numbers": [],
        "clearances": [],
    }
    PROGRESS_FILE.write_text(
        json.dumps(progress, indent=2),
        encoding="utf-8",
    )

    print("C2 continual checkpoint validation: PASS")
    print(f"Completed runs: {CHECKPOINT_RUNS}")
    print(f"Raw lessons: {len(memory)}")
    print(f"Playbook rules: {rule_count}")
    print("Starting Ascension: A0")
    print("Next run number: 16")
    print("Fresh random seeds will be generated and persisted automatically.")
    print(f"Checkpoint copied to: {ARCHIVE_DIR}")
    print("\nNext step:")
    print("  Copy spirecomm/test_connection_c2_continual_v1.py over spirecomm/test_connection.py")
    print("  Then launch reflection/feedback_app.py with condition_c2_outputs and start Slay the Spire.")


if __name__ == "__main__":
    main()
