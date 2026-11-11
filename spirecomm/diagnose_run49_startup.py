"""Read-only offline diagnosis of Run-49 v1.6.1 startup preconditions.

Use from repo root: python spirecomm/diagnose_run49_startup.py
Never launches STS, creates a checkpoint, or modifies memory/events.
"""
from __future__ import annotations

from pathlib import Path
from zipfile import is_zipfile

import test_connection_c2_run49 as run49


def diagnose():
    base = run49.base
    sp = Path(__file__).resolve().parent
    review47 = sp.parent / "reflection/condition_c2_outputs/run_47_feedback_review.json"
    review48 = sp.parent / "reflection/condition_c2_outputs/run_48_feedback_review.json"
    failures = []

    def check(name, fn):
        try:
            info = fn()
            print(f"[PASS] {name}" + (f": {info}" if info else ""))
        except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
            message = f"{type(exc).__name__}: {exc}"
            failures.append((name, message))
            print(f"[FAIL] {name}: {message}")

    def archive(name, path):
        def check_archive():
            if not path.is_file():
                raise ValueError(f"Missing {path}; create the one-time local checkpoint with STS stopped.")
            if not is_zipfile(path):
                raise ValueError(f"Not a readable ZIP archive: {path}")
            return str(path)
        check(name, check_archive)

    print("Run-49 v1.6.1 read-only startup diagnosis")
    print("No game launch or memory/log modification is performed.\n")
    check("Active controller class", lambda: (
        run49.VARIANT if base.STSAgent is run49.ContinualC2Run49Agent
        else (_ for _ in ()).throw(ValueError("Active STSAgent not Run49"))))
    archive("Run-42 historical checkpoint", run49.run48.run43.CHECKPOINT_FILE)
    archive("Run-47 historical checkpoint", run49.run48.CHECKPOINT_FILE)
    archive("Run-48 new checkpoint", run49.CHECKPOINT_FILE)
    check("Run-42 finalization and Neow human rule", lambda:
          run49.run48.run43.verify_run42_cutover(
              base.EVENTS_FILE, base.PLAYBOOK_FILE,
              run49.run48.run43.CHECKPOINT_FILE) and "review/playbook valid")
    check("Run-47 finalized review and playbook", lambda:
          run49.run48.verify_run47_cutover(
              base.EVENTS_FILE, base.PLAYBOOK_FILE, review47,
              run49.run48.CHECKPOINT_FILE) and "review/playbook valid")
    check("Run-48 finalized review and playbook", lambda:
          run49.verify_run48_cutover(
              base.EVENTS_FILE, base.PLAYBOOK_FILE, review48,
              run49.CHECKPOINT_FILE) and "review/playbook valid")
    print()
    if failures:
        print(f"STARTUP NOT READY: {len(failures)} check(s) failed.")
        print("Correct these failures before trying to launch Run 49 again.")
        return 1
    print("RUN-49 STARTUP GATES PASS. If STS still does not start, capture")
    print("the Python controller terminal traceback and latest game/mod logs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(diagnose())
