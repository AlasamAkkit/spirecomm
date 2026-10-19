from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

# One-time research boundary snapshot: Run 36 used v1.3.1; Run 37+
# uses the fixed stable controller. Earlier runs 1-35 are already
# preserved under C2_continual_through_run35_pre_v1_3_1.
CHECKPOINT_RUN = 36
PLAYED_CONTROLLER = "c2-continual-teaching-v1.3.1-block-aware-verifier"
NEXT_CONTROLLER = "c2-continual-teaching-v1.4.0-stable-feedback-loop"

BASE = Path(__file__).resolve().parent
PROJECT = BASE.parent
REFLECTION = PROJECT / "reflection"
DEST = BASE / "runs" / "C2_continual_through_run36_pre_stable"
EVENTS = BASE / "run_events_c2.jsonl"
PLAYBOOK = REFLECTION / "condition_c2_playbook.json"
MEMORY = REFLECTION / "condition_c2_raw_memory.jsonl"
FEEDBACK = REFLECTION / "condition_c2_feedback.jsonl"
OUTPUTS = REFLECTION / "condition_c2_outputs"


def jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON at {path}:{number}") from exc


def main():
    if DEST.exists():
        raise FileExistsError(f"Refusing to overwrite an existing checkpoint: {DEST}")

    required = [
        EVENTS, PLAYBOOK, MEMORY, FEEDBACK,
        BASE / "c2_continual_seed_schedule.json",
        BASE / "c2_continual_progress.json",
        BASE / "test_connection_c2_continual_v1_3_1.py",
        BASE / "test_connection_c2_stable.py",
        BASE / "test_connection_c2_finalize_run36.py",
    ]
    required += [
        OUTPUTS / f"run_{CHECKPOINT_RUN}_feedback_review.json",
        OUTPUTS / f"run_{CHECKPOINT_RUN}_final_reflection.json",
        OUTPUTS / f"run_{CHECKPOINT_RUN}_initial_reflection.json",
        OUTPUTS / f"run_{CHECKPOINT_RUN}_trajectory_v2.txt",
    ]
    missing_paths = [str(p) for p in required if not p.exists()]
    if missing_paths:
        raise FileNotFoundError("Required checkpoint input missing: " + ", ".join(missing_paths))

    run_ends = {}
    reflected = {}
    for row in jsonl(EVENTS):
        n = row.get("completed_run_number")
        if row.get("event_type") == "RUN_END" and isinstance(n, int):
            run_ends[n] = row
        if row.get("event_type") == "POST_RUN_REFLECTION_COMPLETE" and isinstance(n, int):
            reflected[n] = row

    required_runs = set(range(1, CHECKPOINT_RUN + 1))
    if set(run_ends) != required_runs or set(reflected) != required_runs:
        raise ValueError(
            f"Expected all RUN_END/reflection events 1-{CHECKPOINT_RUN}; "
            f"found run_end={sorted(run_ends)}, reflected={sorted(reflected)}"
        )
    if run_ends[CHECKPOINT_RUN].get("continual_controller_version") != PLAYED_CONTROLLER:
        raise ValueError("Run 36 provenance is not v1.3.1.")
    if reflected[CHECKPOINT_RUN].get("playbook_updated_through_run") != CHECKPOINT_RUN:
        raise ValueError("Run 36 reflection does not report updated playbook through 36.")

    pb = json.loads(PLAYBOOK.read_text(encoding="utf-8"))
    if int(pb.get("updated_through_run") or 0) != CHECKPOINT_RUN:
        raise ValueError("Active playbook has not finalized Run 36.")
    review = json.loads(
        (OUTPUTS / f"run_{CHECKPOINT_RUN}_feedback_review.json").read_text(encoding="utf-8")
    )
    if str(review.get("status") or "").upper() == "PENDING":
        raise ValueError("Run 36 feedback is still pending.")
    if not review.get("review_decision"):
        raise ValueError("Run 36 human review decision is missing.")

    raw = list(jsonl(MEMORY))
    rules = [r for rows in pb.get("categories", {}).values() for r in rows]
    covered = {
        mid for rule in rules for mid in (rule.get("source_memory_ids") or [])
    }
    missing = sorted({r["id"] for r in raw} - covered)
    if missing:
        raise ValueError(f"Cumulative memory coverage failure: {missing}")
    fb_count = sum(1 for _ in jsonl(FEEDBACK))
    if fb_count < CHECKPOINT_RUN:
        raise ValueError(f"Expected at least 36 feedback entries, found {fb_count}")

    # Store one compressed bundle, not a duplicate 290-file tree.
    payload = [
        EVENTS, MEMORY, PLAYBOOK, FEEDBACK,
        BASE / "c2_continual_seed_schedule.json",
        BASE / "c2_continual_progress.json",
        *[p for p in required if p.parent == OUTPUTS],
    ]
    deck_plan = REFLECTION / "c2_active_deck_plan.json"
    if deck_plan.exists():
        payload.append(deck_plan)

    DEST.mkdir(parents=True)
    hashes = {}
    zip_path = DEST / "RUN36_DATA_SNAPSHOT.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in payload:
            arcname = str(path.relative_to(PROJECT)).replace("\\", "/")
            archive.write(path, arcname=arcname)
            hashes[arcname] = hashlib.sha256(path.read_bytes()).hexdigest()

    summary = {
        "schema": "c2-continual-stable-boundary-v1",
        "checkpoint_run": CHECKPOINT_RUN,
        "controller_version": PLAYED_CONTROLLER,
        "next_controller": NEXT_CONTROLLER,
        "next_run": 37,
        "run36_result": run_ends[CHECKPOINT_RUN].get("result"),
        "run36_score": run_ends[CHECKPOINT_RUN].get("score"),
        "run36_floor": run_ends[CHECKPOINT_RUN].get("floor"),
        "raw_memory_count": len(raw),
        "playbook_rule_count": len(rules),
        "feedback_rows": fb_count,
        "playbook_updated_through_run": pb.get("updated_through_run"),
        "zip_sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "archived_file_sha256": hashes,
        "research_note": (
            "The stable Run-37+ controller adds only execution safeguards. "
            "Historical controller versions remain unchanged for provenance. "
            "Future model behavior changes are driven by run-specific human teaching."
        ),
    }
    (DEST / "CHECKPOINT_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("C2 STABLE BASELINE CHECKPOINT: PASS")
    print("Completed and reflected runs:", CHECKPOINT_RUN)
    print("Raw lessons:", len(raw))
    print("Playbook rules:", len(rules))
    print("Playbook updated through:", pb.get("updated_through_run"))
    print("Checkpoint:", DEST)
    print("Next run: 37")
    print("Next controller:", NEXT_CONTROLLER)


if __name__ == "__main__":
    main()
