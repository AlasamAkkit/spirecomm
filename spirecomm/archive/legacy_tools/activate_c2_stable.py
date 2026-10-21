from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

# One-time activation helper. It never starts a Slay the Spire run.
# Finish Run 36 feedback/reflection using the v1.3.1 finalize-only
# wrapper and close the game/controller BEFORE running this file.
ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT.parent
STABLE = ROOT / "test_connection_c2_stable.py"
ACTIVE = ROOT / "test_connection.py"
TEST = ROOT / "test_c2_stable_preflight.py"
FREEZER = Path(__file__).resolve().parent / "freeze_c2_run36_stable_baseline.py"
BASELINE = ROOT / "runs" / "C2_continual_through_run36_pre_stable"
PLAYBOOK = PROJECT / "reflection" / "condition_c2_playbook.json"
EVENTS = ROOT / "run_events_c2.jsonl"


def _run(*args: str):
    print("+", " ".join(args), flush=True)
    subprocess.run([sys.executable, *args], check=True, cwd=PROJECT)


def _precondition():
    if not PLAYBOOK.exists() or not EVENTS.exists():
        raise FileNotFoundError("Missing C2 experiment state; wrong project folder?")
    playbook = json.loads(PLAYBOOK.read_text(encoding="utf-8"))
    through = playbook.get("updated_through_run")
    if through != 36:
        raise ValueError(
            f"Run 36 review/reflection must be FINALIZED first; playbook is through {through}."
        )

    ended = False
    reflected = False
    unsafe_next_start = False
    with EVENTS.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            event = json.loads(line)
            if (event.get("event_type") == "RUN_END"
                    and event.get("completed_run_number") == 36):
                ended = True
            if (event.get("event_type") == "POST_RUN_REFLECTION_COMPLETE"
                    and event.get("completed_run_number") == 36):
                reflected = True
            if ended and event.get("event_type") == "RUN_START":
                unsafe_next_start = True

    if not (ended and reflected):
        raise ValueError(
            "Run 36 is not both completed and reflected; stable activation is blocked."
        )
    if unsafe_next_start:
        raise ValueError(
            "A newer run has already started after Run 36. "
            "Do not replace an active controller mid-run."
        )


def _validate_existing_baseline():
    summary_file = BASELINE / "CHECKPOINT_SUMMARY.json"
    zip_path = BASELINE / "RUN36_DATA_SNAPSHOT.zip"
    if not summary_file.is_file() or not zip_path.is_file():
        raise ValueError(
            "Incomplete existing stable checkpoint. Inspect manually; refusing overwrite."
        )
    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    if summary.get("checkpoint_run") != 36 or summary.get("zip_sha256") != digest:
        raise ValueError("Existing stable baseline failed integrity validation.")
    print("Existing Run-36 stable baseline integrity: PASS")


def main():
    _precondition()
    for file in (STABLE, TEST, FREEZER):
        if not file.exists():
            raise FileNotFoundError(f"Missing activation input: {file}")

    # Compile before any snapshot or installation.
    _run("-m", "py_compile", str(STABLE), str(TEST), str(FREEZER))

    if not BASELINE.exists():
        _run(str(FREEZER))
    _validate_existing_baseline()

    # Run the real import/unit tests AFTER all Run-36 review data exists.
    # If ANY assertion fails, ACTIVE is never replaced.
    _run(str(TEST))

    # Atomic swap: the historical v1.3.1 and finalization wrappers remain
    # immutable, and the currently configured test_connection.py only
    # changes after all checks pass.
    temp = ACTIVE.with_suffix(".stable-install.tmp")
    try:
        shutil.copyfile(STABLE, temp)
        temp.replace(ACTIVE)
    finally:
        if temp.exists():
            temp.unlink()

    _run("-m", "py_compile", str(ACTIVE))
    print()
    print("C2 STABLE ACTIVATION: PASS")
    print("Controller: c2-continual-teaching-v1.4.0-stable-feedback-loop")
    print("Next run: 37")
    print("The active test_connection.py is now stable.")
    print("For future runs: give feedback in the web app; do not swap controllers.")


if __name__ == "__main__":
    main()
