"""Freeze the LOCAL, finalized Run-54 C2 boundary before enabling v1.7.

Run only with Slay the Spire and the Python controller stopped.
Write-once: refuses to overwrite an existing archive.
Does not update human feedback, run events, memory or playbook.
"""
from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

SP = Path(__file__).resolve().parent
PROJECT = SP.parent
TARGET = SP / "runs" / "_local_checkpoints" / "C2_through_run54_pre_v1_7.zip"

REQUIRED = [
    "reflection/condition_c2_raw_memory.jsonl",
    "reflection/condition_c2_playbook.json",
    "reflection/condition_c2_feedback.jsonl",
    "spirecomm/run_events_c2.jsonl",
    "reflection/condition_c2_outputs/run_54_feedback_review.json",
    "reflection/condition_c2_outputs/run_54_final_reflection.json",
]
OPTIONAL = [
    "spirecomm/c2_continual_progress.json",
    "spirecomm/c2_continual_seed_schedule.json",
    "spirecomm/sts_messages_c2.log",
    "spirecomm/agent_debug_c2.log",
    "spirecomm/state_dumps_c2.jsonl",
    "reflection/condition_c2_outputs/run_54_raw.json",
    "reflection/condition_c2_outputs/run_54_states.json",
    "reflection/condition_c2_outputs/run_54_trajectory_v2.txt",
    "reflection/condition_c2_outputs/run_54_initial_reflection.json",
    "spirecomm/test_connection_c2_run49.py",
    "spirecomm/test_connection_c2_run48.py",
    "spirecomm/test_connection_c2_run43.py",
    "spirecomm/test_connection_c2_a10.py",
    "spirecomm/test_connection_c2_stable.py",
    "spirecomm/run49_policy.py",
    "spirecomm/run48_policy.py",
    "spirecomm/run43_policy.py",
    "reflection/followup_reflection.py",
]


def validate(project: Path) -> dict:
    missing = [name for name in REQUIRED if not (project / name).is_file()]
    if missing:
        raise ValueError("Missing Run-54 evidence: " + ", ".join(missing))
    book = json.loads((project / REQUIRED[1]).read_text(encoding="utf-8"))
    review = json.loads((project / REQUIRED[4]).read_text(encoding="utf-8"))
    if int(book.get("updated_through_run") or 0) != 54:
        raise ValueError("Expected playbook updated_through_run == 54")
    if review.get("status") != "FINALIZED" or review.get("source_run") != 54:
        raise ValueError("Run-54 review must be FINALIZED with source_run 54")
    if review.get("review_decision") not in {"HUMAN_TEACHING", "APPROVE_INITIAL"}:
        raise ValueError("Run-54 review decision must be approved.")
    if (review["review_decision"] == "HUMAN_TEACHING"
            and not str(review.get("human_feedback") or "").strip()):
        raise ValueError("Run-54 authoritative teaching must not be empty.")
    run_end = reflected = False
    with (project / "spirecomm/run_events_c2.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            if (row.get("completed_run_number") == 54
                    and row.get("run_id") == review.get("source_run_id")
                    and row.get("event_type") == "RUN_END"):
                run_end = True
            if (row.get("completed_run_number") == 54
                    and row.get("reflected_run_id") == review.get("source_run_id")
                    and row.get("event_type") == "POST_RUN_REFLECTION_COMPLETE"):
                reflected = True
    if not (run_end and reflected):
        raise ValueError("Run-54 matching RUN_END/reflection completion not present.")
    return review


def main():
    if TARGET.exists():
        raise SystemExit("Write-once Run-54 checkpoint exists; will not overwrite: " + str(TARGET))
    try:
        packet = validate(PROJECT)
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc)) from exc

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    temp = TARGET.with_suffix(".zip.tmp")
    try:
        with ZipFile(temp, "w", ZIP_DEFLATED, compresslevel=6) as archive:
            for name in REQUIRED + OPTIONAL:
                source = PROJECT / name
                if source.is_file():
                    archive.write(source, arcname=name)
        temp.replace(TARGET)
    finally:
        if temp.exists():
            temp.unlink()
    print("RUN54_CHECKPOINT_OK:", TARGET)
    print("Run-54 review:", packet["review_decision"], "| full memory/playbook/log snapshot preserved")


if __name__ == "__main__":
    main()
