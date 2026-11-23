r"""Create an immutable LOCAL Run-55 post-v1.7 checkpoint.

Usage (PowerShell, from project root with game/controller stopped):
  & .\spirecomm\venv\Scripts\python.exe .\freeze_c2_run55_checkpoint.py

Alternatively put this file in spirecomm/ and run from there.
Do not commit the resulting archive: it contains raw feedback and model logs.
No existing user files, raw memory, or log entries are changed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone
from zipfile import ZipFile, ZIP_DEFLATED, is_zipfile

RUN = 55
ARCHIVE_NAME = "C2_through_run55_post_v1_7.zip"
REQUIRED = [
    "reflection/condition_c2_raw_memory.jsonl",
    "reflection/condition_c2_playbook.json",
    "reflection/condition_c2_feedback.jsonl",
    "spirecomm/run_events_c2.jsonl",
    "reflection/condition_c2_outputs/run_55_feedback_review.json",
    "reflection/condition_c2_outputs/run_55_final_reflection.json",
    "reflection/condition_c2_outputs/run_55_raw.json",
    "reflection/condition_c2_outputs/run_55_states.json",
    "reflection/condition_c2_outputs/run_55_trajectory_v2.txt",
    "reflection/condition_c2_outputs/run_55_initial_reflection.json",
]
OPTIONAL = [
    "reflection/condition_c2_outputs/run_55_initial_reflection_raw.txt",
    "spirecomm/c2_continual_progress.json",
    "spirecomm/c2_continual_seed_schedule.json",
    "spirecomm/sts_messages_c2.log",
    "spirecomm/agent_debug_c2.log",
    "spirecomm/state_dumps_c2.jsonl",
    "spirecomm/test_connection.py",
    "spirecomm/test_connection_c2_run55.py",
    "spirecomm/run55_policy.py",
    "spirecomm/test_c2_run55_preflight.py",
    "spirecomm/test_connection_c2_run49.py",
    "spirecomm/run49_policy.py",
    "spirecomm/test_connection_c2_run48.py",
    "spirecomm/run48_policy.py",
    "spirecomm/test_connection_c2_run43.py",
    "spirecomm/run43_policy.py",
    "spirecomm/test_connection_c2_a10.py",
    "spirecomm/test_connection_c2_stable.py",
    "reflection/followup_reflection.py",
    "reflection/active_review.py",
    "reflection/feedback_app.py",
]


def project_root() -> Path:
    here = Path(__file__).resolve().parent
    for root in (here, here.parent):
        if (root / "spirecomm").is_dir() and (root / "reflection").is_dir():
            return root
    raise SystemExit(
        "Run this from the FYP project, or place this script inside its root/spirecomm folder."
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_info(project: Path) -> dict[str, str]:
    data = {}
    for label, cmd in (
        ("commit", ["git", "rev-parse", "HEAD"]),
        ("branch", ["git", "branch", "--show-current"]),
        ("working_tree_status", ["git", "status", "--porcelain"]),
    ):
        try:
            result = subprocess.run(
                cmd, cwd=project, capture_output=True, text=True, timeout=12,
                check=True, encoding="utf-8", errors="replace",
            )
            data[label] = result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            data[label] = "unavailable"
    return data


def validate(project: Path) -> dict:
    missing = [name for name in REQUIRED if not (project / name).is_file()]
    if missing:
        raise ValueError("Missing required Run-55 evidence:\n- " + "\n- ".join(missing))

    review = json.loads((project / "reflection/condition_c2_outputs/run_55_feedback_review.json").read_text(encoding="utf-8"))
    if review.get("status") != "FINALIZED" or int(review.get("source_run") or 0) != RUN:
        raise ValueError("Run-55 review is not FINALIZED with source_run == 55")
    decision = review.get("review_decision")
    if decision not in {"APPROVE_INITIAL", "HUMAN_TEACHING"}:
        raise ValueError("Run-55 review_decision is missing or invalid")
    if decision == "HUMAN_TEACHING" and not str(review.get("human_feedback") or "").strip():
        raise ValueError("Run-55 HUMAN_TEACHING text is empty")

    source_run_id = review.get("source_run_id")
    if not isinstance(source_run_id, str) or not source_run_id.strip():
        raise ValueError("Run-55 review source_run_id is missing")

    book = json.loads((project / "reflection/condition_c2_playbook.json").read_text(encoding="utf-8"))
    book_run = int(book.get("updated_through_run") or 0)
    if book_run != RUN:
        raise ValueError(f"Expected playbook updated_through_run == 55, got {book_run}; freeze immediately after Run 55, before Run 56")

    final = json.loads((project / "reflection/condition_c2_outputs/run_55_final_reflection.json").read_text(encoding="utf-8"))
    if int(final.get("source_run") or 0) != RUN or final.get("source_run_id") != source_run_id:
        raise ValueError("Run-55 final reflection does not match finalized review's run ID")

    has_end = has_reflection = False
    with (project / "spirecomm/run_events_c2.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            event = json.loads(line)
            if (event.get("completed_run_number") == RUN
                    and event.get("run_id") == source_run_id
                    and event.get("event_type") == "RUN_END"):
                has_end = True
            if (event.get("completed_run_number") == RUN
                    and event.get("reflected_run_id") == source_run_id
                    and event.get("event_type") == "POST_RUN_REFLECTION_COMPLETE"):
                has_reflection = True
    if not has_end or not has_reflection:
        raise ValueError(
            f"Run-55 ledger boundary incomplete (RUN_END={has_end}, POST_RUN_REFLECTION_COMPLETE={has_reflection})"
        )

    return {"review_decision": decision, "source_run_id": source_run_id,
            "playbook_updated_through_run": book_run}


def main():
    project = project_root()
    target = project / "spirecomm" / "runs" / "_local_checkpoints" / ARCHIVE_NAME
    if target.exists():
        raise SystemExit("Write-once checkpoint already exists; refusing overwrite: " + str(target))

    try:
        validation = validate(project)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit("RUN55_CHECKPOINT_BLOCKED: " + str(exc)) from exc

    entries = []
    for name in REQUIRED + OPTIONAL:
        file = project / name
        if file.is_file():
            entries.append({"path": name, "size_bytes": file.stat().st_size,
                            "sha256": sha256_file(file), "required": name in REQUIRED})

    manifest = {
        "checkpoint": "C2_through_run55_post_v1_7",
        "checkpoint_type": "local_write_once_post_finalized_feedback",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "run": RUN,
        "controller_variant": "c2-v1.7.0-run55-context-memory-json-safety+a10",
        "validation": validation,
        "git": git_info(project),
        "files": entries,
        "note": "Do not push to GitHub: contains raw experiments, reflections, private logs and feedback.",
    }

    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".tmp")
    if temp.exists():
        raise SystemExit("An unfinished temporary checkpoint exists; inspect it before retrying: " + str(temp))
    try:
        with ZipFile(temp, "w", ZIP_DEFLATED, compresslevel=5, allowZip64=True) as archive:
            for entry in entries:
                src = project / entry["path"]
                if sha256_file(src) != entry["sha256"]:
                    raise ValueError("Source file changed during checkpoint creation: " + entry["path"])
                archive.write(src, arcname=entry["path"])
            archive.writestr("CHECKPOINT_MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
        if not is_zipfile(temp):
            raise ValueError("Checkpoint ZIP integrity check failed")
        with ZipFile(temp, "r") as archive:
            invalid_member = archive.testzip()
            if invalid_member:
                raise ValueError("ZIP member integrity check failed: " + invalid_member)
        # Ensure write-once even on platforms with concurrent runs.
        if target.exists():
            raise ValueError("Checkpoint target appeared during creation; refusing overwrite")
        os.rename(temp, target)
    finally:
        if temp.exists():
            temp.unlink()

    print("RUN55_CHECKPOINT_OK:", target)
    print("Run 55:", validation["review_decision"], "| all required evidence validated")
    print("Files preserved:", len(entries), "| SHA256 manifest inside ZIP")
    print("Preserve this ZIP locally. Do not commit/push it to GitHub.")


if __name__ == "__main__":
    main()
