"""Safely finalize an already-reviewed C2 run without starting Slay the Spire.

From the repository root:
    python spirecomm/finalize_pending_review.py --run 38

Stop the game/controller first. Finalize feedback using the existing local web
app, then run this script. It DOES NOT call the CommunicationMod event loop,
write a START command, or start a new game. It preserves a pre-finalization
checkpoint of research data before any mutation.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "spirecomm"))
sys.path.insert(0, str(ROOT / "reflection"))

from reflection.followup_reflection import find_unprocessed_completed_runs
from test_connection_c2_stable import ContinualC2StableAgent, base

PLAYBOOK_FILE = ROOT / "reflection" / "condition_c2_playbook.json"
OUTPUT_DIR = ROOT / "reflection" / "condition_c2_outputs"
CHECKPOINT_ROOT = ROOT / "spirecomm" / "runs"


def _events(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=int, required=True)
    args = parser.parse_args()
    run_number = args.run
    if run_number < 16:
        raise SystemExit("Only post-checkpoint continual C2 runs are supported.")

    events_file = Path(base.EVENTS_FILE)
    review_file = OUTPUT_DIR / f"run_{run_number:02d}_feedback_review.json"
    if not events_file.is_file() or not review_file.is_file():
        raise SystemExit("Missing event log or feedback review packet.")
    review = json.loads(review_file.read_text(encoding="utf-8"))
    if review.get("source_run") != run_number or review.get("status") != "FINALIZED":
        raise SystemExit("First finalize this exact run in the existing feedback UI.")

    events = _events(events_file)
    end_indices = [
        i for i, row in enumerate(events)
        if row.get("event_type") == "RUN_END"
        and row.get("completed_run_number") == run_number
        and row.get("run_id") == review.get("source_run_id")
    ]
    if len(end_indices) != 1:
        raise SystemExit("Expected exactly one matching RUN_END; refusing to mutate data.")
    if any(row.get("event_type") == "RUN_START" for row in events[end_indices[0] + 1:]):
        raise SystemExit("A subsequent run has already started; cannot establish this boundary.")

    pending = find_unprocessed_completed_runs(events_file)
    if pending and (
        len(pending) != 1
        or pending[0].get("completed_run_number") != run_number
        or pending[0].get("run_id") != review.get("source_run_id")
    ):
        raise SystemExit(f"Unexpected unprocessed runs: {pending!r}")

    checkpoint = CHECKPOINT_ROOT / f"C2_through_run{run_number:02d}_pre_A10"
    checkpoint.mkdir(parents=True, exist_ok=True)
    to_preserve = [
        events_file,
        Path(base.LOG_FILE),
        Path(base.MEMORY_FILE),
        Path(base.PLAYBOOK_FILE),
        Path(base.FEEDBACK_BANK_FILE),
        review_file,
        OUTPUT_DIR / f"run_{run_number:02d}_initial_reflection.json",
        OUTPUT_DIR / f"run_{run_number:02d}_trajectory_v2.txt",
    ]
    for original in to_preserve:
        if original.is_file():
            shutil.copy2(original, checkpoint / original.name)
    print(f"Pre-finalization research snapshot: {checkpoint}")

    if pending:
        # Importing/instantiating the stable agent does NOT launch the game;
        # only its main() drives CommunicationMod and starts subsequent runs.
        agent = ContinualC2StableAgent(use_llm=True, enable_logging=True)
        agent.recover_pending_reflections()
        agent.validate_followup_integrity()

    final_events = _events(events_file)
    if not any(
        row.get("event_type") == "POST_RUN_REFLECTION_COMPLETE"
        and row.get("completed_run_number") == run_number
        for row in final_events
    ):
        raise SystemExit("Run review processed without reflection-complete event.")
    playbook = json.loads(PLAYBOOK_FILE.read_text(encoding="utf-8"))
    if int(playbook.get("updated_through_run") or 0) != run_number:
        raise SystemExit("Playbook is not updated through the requested run.")
    print(f"SUCCESS: Run {run_number} finalized; memory/playbook updated.")
    print("No gameplay loop was launched. Keep Slay the Spire closed until the A10 policy is installed.")


if __name__ == "__main__":
    main()
