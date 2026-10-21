"""C2 A10 stress phase: fixed Ascension 10 from Run 39 onward.

Preserves the tested v1.4.0 gameplay decision/controller behavior, human
teaching, complete cumulative retrieval and existing run logs. Only the
difficulty schedule changes at an explicitly recorded intervention boundary.

DO NOT activate until Run 38 has POST_RUN_REFLECTION_COMPLETE and the
playbook is updated through Run 38. Use finalize_pending_review.py first.
"""
from __future__ import annotations

import json
from pathlib import Path

import test_connection_c2_stable as stable

A10_START_RUN = 39
A10_ASCENSION = 10
A10_POLICY = "fixed-a10-from-run39-v1"
CONTROLLER_VARIANT = "c2-v1.4.0-stable+a10-difficulty-policy-v1"

base = stable.base


class ContinualC2A10Agent(stable.ContinualC2StableAgent):
    def _rebuild_progress_from_events(self):
        progress = super()._rebuild_progress_from_events()
        completed = progress.get("processed_run_numbers") or []
        # The ledger is authoritative. Never forge a prior A10 clearance and
        # never modify old RUN_END entries to make a jump appear sequential.
        if completed and max(completed) >= A10_START_RUN - 1:
            progress["current_ascension"] = A10_ASCENSION
            progress["difficulty_policy"] = A10_POLICY
            progress["difficulty_override_start_run"] = A10_START_RUN
        return progress

    def log_run_event(self, event_type, game_state=None, **details):
        details.setdefault("controller_variant", CONTROLLER_VARIANT)
        details.setdefault("difficulty_policy", A10_POLICY)
        details.setdefault("difficulty_override_start_run", A10_START_RUN)
        return super().log_run_event(event_type, game_state, **details)

    def __init__(self, *args, **kwargs):
        # Validate the recorded phase boundary BEFORE parent initialization
        # can derive and write the new A10 progress sidecar.
        events_file = Path(base.EVENTS_FILE)
        finalized = False
        if events_file.is_file():
            for line in events_file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if (
                    row.get("event_type") == "POST_RUN_REFLECTION_COMPLETE"
                    and row.get("completed_run_number") == A10_START_RUN - 1
                ):
                    finalized = True
        if not finalized:
            raise ValueError(
                "Run 38 not finalized. Stop controller, finalize human review "
                "offline, and use finalize_pending_review.py --run 38 first."
            )
        super().__init__(*args, **kwargs)
        if self.completed_run_count < A10_START_RUN - 1:
            raise ValueError("A10 requires Run 38 to be completed.")
        if int(self.playbook.get("updated_through_run") or 0) < A10_START_RUN - 1:
            raise ValueError("Run 38 lesson is not yet in the playbook.")
        if int(base.ASCENSION) != A10_ASCENSION:
            raise ValueError(f"Expected A{A10_ASCENSION}; got A{base.ASCENSION}.")


# Same main() and CommunicationMod loop as the v1.4.0 stable system.
base.STSAgent = ContinualC2A10Agent


def main():
    stable.main()


if __name__ == "__main__":
    main()
