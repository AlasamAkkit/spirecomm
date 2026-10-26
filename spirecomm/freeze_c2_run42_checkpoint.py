"""Create an immutable offline Run-42 boundary archive, without launching a game.

Usage with the controller stopped:
    python spirecomm/freeze_c2_run42_checkpoint.py
"""
from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

SP = Path(__file__).resolve().parent
PROJECT = SP.parent
TARGET = SP / "runs" / "_local_checkpoints" / "C2_through_run42_pre_v1_5.zip"

REQUIRED = [
    "reflection/condition_c2_raw_memory.jsonl",
    "reflection/condition_c2_playbook.json",
    "reflection/condition_c2_feedback.jsonl",
    "spirecomm/run_events_c2.jsonl",
    "reflection/condition_c2_outputs/run_42_feedback_review.json",
]
OPTIONAL = [
    "spirecomm/c2_continual_progress.json",
    "spirecomm/c2_continual_seed_schedule.json",
    "spirecomm/sts_messages_c2.log",
    "spirecomm/agent_debug_c2.log",
    "spirecomm/state_dumps_c2.jsonl",
    "reflection/condition_c2_outputs/run_42_raw.json",
    "reflection/condition_c2_outputs/run_42_states.json",
    "reflection/condition_c2_outputs/run_42_trajectory_v2.txt",
    "reflection/condition_c2_outputs/run_42_initial_reflection.json",
    "reflection/condition_c2_outputs/run_42_final_reflection.json",
    "spirecomm/test_connection.py",
    "spirecomm/test_connection_c2_a10.py",
    "spirecomm/test_connection_c2_stable.py",
]
def main():
    if TARGET.exists():
        raise SystemExit("Run-42 checkpoint already exists; will not overwrite: " + str(TARGET))
    missing = [str(p) for p in REQUIRED if not (PROJECT / p).is_file()]
    if missing:
        raise SystemExit("Missing required evidence: " + ", ".join(missing))
    playbook = json.loads((PROJECT / REQUIRED[1]).read_text(encoding="utf-8"))
    packet = json.loads((PROJECT / REQUIRED[-1]).read_text(encoding="utf-8"))
    if int(playbook.get("updated_through_run") or 0) != 42:
        raise SystemExit("Expected playbook updated_through_run == 42")
    if packet.get("status") != "FINALIZED":
        raise SystemExit("Run-42 review must be FINALIZED")
    if packet.get("review_decision") not in {"HUMAN_TEACHING", "APPROVE_INITIAL"}:
        raise SystemExit("Run-42 review decision missing")
    finalized = False
    with (PROJECT / "spirecomm/run_events_c2.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                event = json.loads(line)
                if (event.get("event_type") == "POST_RUN_REFLECTION_COMPLETE" and
                        int(event.get("completed_run_number") or 0) == 42):
                    finalized = True
    if not finalized:
        raise SystemExit("Run-42 POST_RUN_REFLECTION_COMPLETE event missing")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    tmp = TARGET.with_suffix(".zip.tmp")
    try:
        with ZipFile(tmp, "w", ZIP_DEFLATED, compresslevel=6) as archive:
            for path in REQUIRED + OPTIONAL:
                source = PROJECT / path
                if source.is_file():
                    archive.write(source, arcname=path)
        tmp.replace(TARGET)
    finally:
        if tmp.exists():
            tmp.unlink()
    print(f"Run-42 checkpoint written: {TARGET}")
    print(f"Playbook through 42; review={packet['review_decision']}; sources preserved")


if __name__ == "__main__":
    main()
