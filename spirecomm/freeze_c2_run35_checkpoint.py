from __future__ import annotations

import json
import shutil
from pathlib import Path

CHECKPOINT_RUN = 35
EXPECTED_RUN35_CONTROLLER = "c2-continual-teaching-v1.3.0-cumulative-policy-verified-planning"
NEXT_CONTROLLER = "c2-continual-teaching-v1.3.1-block-aware-verifier"

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
REFLECTION_DIR = PROJECT_DIR / "reflection"
ARCHIVE_DIR = BASE_DIR / "runs" / "C2_continual_through_run35_pre_v1_3_1"

EVENTS_FILE = BASE_DIR / "run_events_c2.jsonl"
MEMORY_FILE = REFLECTION_DIR / "condition_c2_raw_memory.jsonl"
PLAYBOOK_FILE = REFLECTION_DIR / "condition_c2_playbook.json"
FEEDBACK_FILE = REFLECTION_DIR / "condition_c2_feedback.jsonl"
OUTPUT_DIR = REFLECTION_DIR / "condition_c2_outputs"
SEED_FILE = BASE_DIR / "c2_continual_seed_schedule.json"
PROGRESS_FILE = BASE_DIR / "c2_continual_progress.json"
DECK_PLAN_FILE = REFLECTION_DIR / "c2_active_deck_plan.json"

CONTROLLERS = [
    BASE_DIR / "test_connection_c2_continual_v1.py",
    BASE_DIR / "test_connection_c2_continual_v1_1.py",
    BASE_DIR / "test_connection_c2_continual_v1_1_1.py",
    BASE_DIR / "test_connection_c2_continual_v1_1_2.py",
    BASE_DIR / "test_connection_c2_continual_v1_2.py",
    BASE_DIR / "test_connection_c2_continual_v1_2_1.py",
    BASE_DIR / "test_connection_c2_continual_v1_3.py",
    BASE_DIR / "test_connection_c2_finalize_run32.py",
    BASE_DIR / "test_connection_c2_finalize_run33.py",
    BASE_DIR / "test_connection_c2_finalize_run35.py",
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
        BASE_DIR / "test_connection_c2_continual_v1_3.py",
        BASE_DIR / "test_connection_c2_finalize_run35.py",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing Run-35 checkpoint file(s):\n- " + "\n- ".join(missing)
        )

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

    run35 = run_ends[CHECKPOINT_RUN]
    if run35.get("continual_controller_version") != EXPECTED_RUN35_CONTROLLER:
        raise ValueError(
            "Run 35 controller does not match v1.3.0: "
            f"{run35.get('continual_controller_version')!r}"
        )

    reflection35 = reflections[CHECKPOINT_RUN]
    if reflection35.get("playbook_updated_through_run") != CHECKPOINT_RUN:
        raise ValueError(
            "Run 35 reflection event does not report playbook_updated_through_run=35: "
            f"{reflection35.get('playbook_updated_through_run')!r}"
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
            f"Feedback bank has only {len(feedback_rows)} rows; "
            f"expected at least {CHECKPOINT_RUN}."
        )

    run35_review = OUTPUT_DIR / "run_35_feedback_review.json"
    run35_final = OUTPUT_DIR / "run_35_final_reflection.json"
    if not run35_review.exists() or not run35_final.exists():
        raise ValueError("Run 35 feedback/final-reflection artifacts are incomplete.")

    review = json.loads(run35_review.read_text(encoding="utf-8"))
    if str(review.get("status", "")).upper() == "PENDING":
        raise ValueError("Run 35 feedback review is still PENDING.")

    if ARCHIVE_DIR.exists():
        raise FileExistsError(f"Checkpoint already exists; refusing to overwrite: {ARCHIVE_DIR}")
    ARCHIVE_DIR.mkdir(parents=True)

    copies = {
        EVENTS_FILE: "run_events_c2.jsonl",
        MEMORY_FILE: "condition_c2_raw_memory.jsonl",
        PLAYBOOK_FILE: "condition_c2_playbook.json",
        FEEDBACK_FILE: "condition_c2_feedback.jsonl",
        SEED_FILE: "c2_continual_seed_schedule.json",
        PROGRESS_FILE: "c2_continual_progress.json",
    }
    if DECK_PLAN_FILE.exists():
        copies[DECK_PLAN_FILE] = "c2_active_deck_plan.json"

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
        "controller_version": EXPECTED_RUN35_CONTROLLER,
        "decision_architecture": run35.get("decision_architecture"),
        "run_35_result": run35.get("result"),
        "run_35_floor": run35.get("floor"),
        "run_35_score": run35.get("score"),
        "run_35_ascension": run35.get("active_ascension"),
        "raw_memory_count": len(memory),
        "playbook_rule_count": len(rules),
        "playbook_updated_through_run": playbook.get("updated_through_run"),
        "feedback_row_count": len(feedback_rows),
        "next_run": CHECKPOINT_RUN + 1,
        "next_controller": NEXT_CONTROLLER,
        "research_note": (
            "Run 35 was the first v1.3 cumulative-policy and verified-planning run. "
            "The Run-13 Centurion/Mystic lesson remained available and the verifier "
            "was operational, but defensive estimates could overstate block while "
            "Frail was active. Run 36 is reserved for v1.3.1 block-aware verification."
        ),
    }
    (ARCHIVE_DIR / "CHECKPOINT_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("C2 continual Run-35 checkpoint validation: PASS")
    print(f"Completed/reflected runs: {CHECKPOINT_RUN}")
    print(f"Raw lessons: {len(memory)}")
    print(f"Playbook rules: {len(rules)}")
    print(f"Playbook updated through: {playbook.get('updated_through_run')}")
    print(f"Feedback rows: {len(feedback_rows)}")
    print(f"Checkpoint copied to: {ARCHIVE_DIR}")
    print("Next run: 36")
    print(f"Next controller: {NEXT_CONTROLLER}")


if __name__ == "__main__":
    main()
