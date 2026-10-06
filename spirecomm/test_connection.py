from __future__ import annotations

import importlib.util
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ============================================================
# CONTINUAL C2 WRAPPER
# ============================================================
#
# This file deliberately does NOT duplicate the validated C2 v1.2.1 gameplay
# controller. It loads the frozen controller from the final matched-experiment
# archive and changes only the run-management policy needed for the open-ended
# teaching phase:
#
# - preserve the completed Run-1..15 C2 history and learned memory;
# - continue numbering at Run 16;
# - generate one fresh persistent random seed for every new run;
# - keep authoritative human teaching exactly as in C2 v1.2.1;
# - advance Ascension by one after the first win at the current level;
# - retain the same gameplay, retrieval, reflection, validation and safety code.
#
# CommunicationMod can point directly at this file, or this file can be copied
# over spirecomm/test_connection.py.

CONTINUAL_CONTROLLER_VERSION = "c2-continual-teaching-v1.0"
RESEARCH_PHASE = "continual_teaching"
CHECKPOINT_COMPLETED_RUNS = 15
CHECKPOINT_RAW_LESSONS = 25
CHECKPOINT_PLAYBOOK_RULES = 17
MAX_ASCENSION = 20
OPEN_ENDED_MAX_COMPLETED_RUNS = 10_000

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
REFLECTION_DIR = PROJECT_DIR / "reflection"
ARCHIVED_CONTROLLER = (
    BASE_DIR
    / "runs"
    / "C2_v1_2_1_15runs_final"
    / "test_connection_c2_v1_2_1.py"
)

SEED_STATE_FILE = BASE_DIR / "c2_continual_seed_schedule.json"
PROGRESS_FILE = BASE_DIR / "c2_continual_progress.json"

HISTORICAL_MATCHED_SEEDS = [
    "260925001",
    "260925002",
    "260925003",
    "260925004",
    "260925005",
    "260925006",
    "260925007",
    "260925008",
    "260925009",
    "260925010",
    "260925011",
    "260925012",
    "260925013",
    "260925014",
    "260925015",
]

if not ARCHIVED_CONTROLLER.exists():
    raise FileNotFoundError(
        "Frozen C2 v1.2.1 controller is missing: " + str(ARCHIVED_CONTROLLER)
    )

# The archived controller computes its own paths from __file__. Ensure the real
# reflection directory is importable before loading it, then patch its active
# file paths back to the project working locations below.
if str(REFLECTION_DIR) not in sys.path:
    sys.path.insert(0, str(REFLECTION_DIR))

_spec = importlib.util.spec_from_file_location(
    "_c2_v121_frozen_controller",
    ARCHIVED_CONTROLLER,
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Could not load the frozen C2 v1.2.1 controller.")

base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

# Keep using the original active C2 working state. The Run-15 checkpoint is
# frozen separately under spirecomm/runs/C2_v1_2_1_15runs_final/.
base.BASE_DIR = BASE_DIR
base.PROJECT_DIR = PROJECT_DIR
base.REFLECTION_DIR = REFLECTION_DIR
base.MEMORY_FILE = REFLECTION_DIR / "condition_c2_raw_memory.jsonl"
base.PLAYBOOK_FILE = REFLECTION_DIR / "condition_c2_playbook.json"
base.FEEDBACK_BANK_FILE = REFLECTION_DIR / "condition_c2_feedback.jsonl"
base.REFLECTION_OUTPUT_DIR = REFLECTION_DIR / "condition_c2_outputs"

base.LOG_FILE = BASE_DIR / "sts_messages_c2.log"
base.DEBUG_FILE = BASE_DIR / "agent_debug_c2.log"
base.EVENTS_FILE = BASE_DIR / "run_events_c2.jsonl"
base.STATE_DUMPS_FILE = BASE_DIR / "state_dumps_c2.jsonl"
base.PAUSE_FILE = BASE_DIR / "EXPERIMENT_PAUSED_C2.txt"
base.SESSION_COMPLETE_FILE = BASE_DIR / "SESSION_COMPLETE_C2.txt"
base.HUMAN_FEEDBACK_REQUIRED_FILE = BASE_DIR / "HUMAN_FEEDBACK_REQUIRED_C2.txt"

# Retain the original v1.2.1 agent/experiment identity so the frozen
# controller's integrity checks see Runs 1..15 and Runs 16+ as one continuous
# memory lineage. New events are explicitly marked with the continual phase and
# wrapper version by the subclass below.
base.MAX_COMPLETED_RUNS = OPEN_ENDED_MAX_COMPLETED_RUNS
base.SESSION_COMPLETED_RUNS = OPEN_ENDED_MAX_COMPLETED_RUNS


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(document, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temp.replace(path)


class PersistentRandomSeedSchedule:
    """Crash-safe random seed provider used by the frozen controller.

    The frozen controller indexes EXPERIMENT_SEEDS using completed_run_count.
    Runs 1..15 therefore resolve to the original matched seeds, while every
    later index is assigned a fresh random nine-digit seed exactly once and
    persisted before START is issued. Re-accessing the same index after a
    restart returns the same stored seed rather than silently changing a run.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self._assignments: dict[str, str] = {}
        if self.path.exists():
            document = json.loads(self.path.read_text(encoding="utf-8"))
            assignments = document.get("assignments", {})
            if not isinstance(assignments, dict):
                raise ValueError("Invalid continual seed schedule assignments.")
            self._assignments = {
                str(k): str(v)
                for k, v in assignments.items()
            }

        self._used = set(HISTORICAL_MATCHED_SEEDS)
        self._used.update(self._assignments.values())

    def __len__(self) -> int:
        return OPEN_ENDED_MAX_COMPLETED_RUNS

    def __getitem__(self, completed_run_index: int) -> str:
        if not isinstance(completed_run_index, int) or completed_run_index < 0:
            raise IndexError(completed_run_index)

        if completed_run_index < CHECKPOINT_COMPLETED_RUNS:
            return HISTORICAL_MATCHED_SEEDS[completed_run_index]

        run_number = completed_run_index + 1
        key = str(run_number)
        existing = self._assignments.get(key)
        if existing:
            return existing

        # Use the OS CSPRNG simply as a convenient source of independent seeds.
        # No cryptographic property is required by the experiment.
        while True:
            candidate = str(100_000_000 + secrets.randbelow(900_000_000))
            if candidate not in self._used:
                break

        self._assignments[key] = candidate
        self._used.add(candidate)
        _atomic_write_json(
            self.path,
            {
                "schema": "c2-continual-random-seeds-v1",
                "updated_at": _utc_now_iso(),
                "checkpoint_completed_runs": CHECKPOINT_COMPLETED_RUNS,
                "assignments": self._assignments,
            },
        )
        return candidate


base.EXPERIMENT_SEEDS = PersistentRandomSeedSchedule(SEED_STATE_FILE)


BaseSTSAgent = base.STSAgent


class ContinualC2Agent(BaseSTSAgent):
    """C2 v1.2.1 with open-ended run and Ascension progression management."""

    def __init__(self, *args, **kwargs):
        self._continual_progress = self._rebuild_progress_from_events()
        self._write_progress()
        base.ASCENSION = int(self._continual_progress["current_ascension"])
        super().__init__(*args, **kwargs)
        self._validate_continual_checkpoint()
        self.log_debug(
            "CONTINUAL_C2_READY: "
            f"completed_runs={self.completed_run_count}, "
            f"raw_memory={len(self.memory_items)}, "
            f"playbook_rules={sum(len(v) for v in self.playbook.get('categories', {}).values())}, "
            f"ascension={base.ASCENSION}."
        )

    # --------------------------------------------------------
    # CONTINUAL-PHASE METADATA
    # --------------------------------------------------------

    def log_run_event(self, event_type, game_state=None, **details):
        # Runs after the frozen checkpoint are part of the longitudinal teaching
        # phase. Keep the original agent/experiment identifiers for the base
        # integrity machinery, but add explicit phase/version metadata.
        completed_before_event = int(getattr(self, "completed_run_count", 0) or 0)
        if completed_before_event >= CHECKPOINT_COMPLETED_RUNS:
            details.setdefault("research_phase", RESEARCH_PHASE)
            details.setdefault(
                "continual_controller_version",
                CONTINUAL_CONTROLLER_VERSION,
            )
            details.setdefault("checkpoint_completed_runs", CHECKPOINT_COMPLETED_RUNS)
            details.setdefault("active_ascension", int(base.ASCENSION))
        return super().log_run_event(event_type, game_state, **details)

    # --------------------------------------------------------
    # ASCENSION PROGRESSION
    # --------------------------------------------------------

    @staticmethod
    def _empty_progress() -> dict[str, Any]:
        return {
            "schema": "c2-continual-progress-v1",
            "checkpoint_completed_runs": CHECKPOINT_COMPLETED_RUNS,
            "current_ascension": 0,
            "highest_cleared_ascension": -1,
            "processed_run_numbers": [],
            "clearances": [],
            "updated_at": _utc_now_iso(),
        }

    def _rebuild_progress_from_events(self) -> dict[str, Any]:
        """Reconstruct Ascension state from RUN_END records every startup.

        The event log is the source of truth. This makes progression recovery
        safe even if the process dies after a winning RUN_END/reflection but
        before the derived progress sidecar is written.
        """
        progress = self._empty_progress()
        if not base.EVENTS_FILE.exists():
            return progress

        events = []
        with base.EVENTS_FILE.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON in {base.EVENTS_FILE} line {line_number}"
                    ) from exc
                if (
                    event.get("event_type") == "RUN_END"
                    and isinstance(event.get("completed_run_number"), int)
                    and event["completed_run_number"] > CHECKPOINT_COMPLETED_RUNS
                ):
                    events.append(event)

        events.sort(key=lambda e: e["completed_run_number"])
        current_ascension = 0
        highest_cleared = -1
        processed = []
        clearances = []

        for event in events:
            run_number = int(event["completed_run_number"])
            ascension = int(event.get("active_ascension", current_ascension))
            processed.append(run_number)

            if str(event.get("result", "")).upper() == "WIN":
                highest_cleared = max(highest_cleared, ascension)
                clearances.append(
                    {
                        "run_number": run_number,
                        "run_id": event.get("run_id"),
                        "ascension": ascension,
                    }
                )
                if ascension >= current_ascension and ascension < MAX_ASCENSION:
                    current_ascension = ascension + 1
                elif ascension == MAX_ASCENSION:
                    current_ascension = MAX_ASCENSION

        progress.update(
            {
                "current_ascension": current_ascension,
                "highest_cleared_ascension": highest_cleared,
                "processed_run_numbers": sorted(set(processed)),
                "clearances": clearances,
                "updated_at": _utc_now_iso(),
            }
        )
        return progress

    def _write_progress(self) -> None:
        _atomic_write_json(PROGRESS_FILE, self._continual_progress)

    def _progress_update_already_logged(self, completed_run_number: int) -> bool:
        if not base.EVENTS_FILE.exists():
            return False
        with base.EVENTS_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                event = json.loads(line)
                if (
                    event.get("event_type") == "CONTINUAL_PROGRESS_UPDATE"
                    and event.get("completed_run_number") == completed_run_number
                ):
                    return True
        return False

    def _refresh_progress_after_run(
        self,
        completed_run_number: int,
        run_id: str,
        game_state=None,
    ) -> None:
        if completed_run_number <= CHECKPOINT_COMPLETED_RUNS:
            return

        previous_ascension = int(self._continual_progress["current_ascension"])
        self._continual_progress = self._rebuild_progress_from_events()
        self._write_progress()
        next_ascension = int(self._continual_progress["current_ascension"])
        base.ASCENSION = next_ascension

        run_end = None
        with base.EVENTS_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                event = json.loads(line)
                if (
                    event.get("event_type") == "RUN_END"
                    and event.get("completed_run_number") == completed_run_number
                    and event.get("run_id") == run_id
                ):
                    run_end = event

        if run_end is None:
            raise ValueError(
                f"Could not find RUN_END for continual run {completed_run_number}."
            )

        completed_ascension = int(
            run_end.get("active_ascension", previous_ascension)
        )
        completed_result = str(run_end.get("result", "")).upper()
        advanced = next_ascension > completed_ascension

        if not self._progress_update_already_logged(completed_run_number):
            self.log_run_event(
                "CONTINUAL_PROGRESS_UPDATE",
                game_state or {},
                completed_run_number=completed_run_number,
                reflected_run_id=run_id,
                completed_result=completed_result,
                completed_ascension=completed_ascension,
                ascension_advanced=advanced,
                next_ascension=next_ascension,
                highest_cleared_ascension=self._continual_progress[
                    "highest_cleared_ascension"
                ],
            )

        if completed_result == "WIN":
            self.log_debug(
                "ASCENSION_CLEAR: "
                f"run={completed_run_number}, cleared=A{completed_ascension}, "
                f"next=A{next_ascension}."
            )

    def process_post_run_reflection(
        self,
        completed_run_number,
        run_id,
        game_state=None,
        recovery=False,
    ):
        result = super().process_post_run_reflection(
            completed_run_number,
            run_id,
            game_state=game_state,
            recovery=recovery,
        )
        self._refresh_progress_after_run(
            completed_run_number,
            run_id,
            game_state=game_state,
        )
        return result

    def reset_for_new_run(self):
        # Rebuild before every new run so even a recovered winning episode cannot
        # leave the controller on a stale Ascension setting.
        self._continual_progress = self._rebuild_progress_from_events()
        self._write_progress()
        base.ASCENSION = int(self._continual_progress["current_ascension"])
        return super().reset_for_new_run()

    # --------------------------------------------------------
    # CHECKPOINT VALIDATION
    # --------------------------------------------------------

    @staticmethod
    def _source_run_number(item: dict[str, Any]) -> int | None:
        try:
            return int(item.get("source_run"))
        except (TypeError, ValueError):
            return None

    def _validate_continual_checkpoint(self) -> None:
        if self.completed_run_count < CHECKPOINT_COMPLETED_RUNS:
            raise ValueError(
                "Continual C2 requires the completed 15-run C2 v1.2.1 checkpoint; "
                f"event log currently has only {self.completed_run_count} completed runs."
            )

        checkpoint_items = []
        for item in self.memory_items:
            source_run = self._source_run_number(item)
            if source_run is not None and source_run <= CHECKPOINT_COMPLETED_RUNS:
                checkpoint_items.append(item)
        if len(checkpoint_items) != CHECKPOINT_RAW_LESSONS:
            raise ValueError(
                "Run-15 C2 checkpoint raw-memory mismatch: expected "
                f"{CHECKPOINT_RAW_LESSONS}, found {len(checkpoint_items)}."
            )

        if self.completed_run_count == CHECKPOINT_COMPLETED_RUNS:
            playbook_rule_count = sum(
                len(v) for v in self.playbook.get("categories", {}).values()
            )
            if playbook_rule_count != CHECKPOINT_PLAYBOOK_RULES:
                raise ValueError(
                    "Run-15 C2 checkpoint playbook mismatch: expected "
                    f"{CHECKPOINT_PLAYBOOK_RULES}, found {playbook_rule_count}."
                )
            if int(self.playbook.get("updated_through_run") or 0) != 15:
                raise ValueError(
                    "Run-15 C2 checkpoint playbook must be updated through Run 15."
                )

        if self.completed_run_count >= OPEN_ENDED_MAX_COMPLETED_RUNS:
            raise ValueError(
                "Open-ended safety ceiling reached; raise OPEN_ENDED_MAX_COMPLETED_RUNS "
                "explicitly rather than silently wrapping run numbering."
            )


# Make the frozen controller's main() construct the continual subclass.
base.STSAgent = ContinualC2Agent


def main():
    base.main()


if __name__ == "__main__":
    main()
