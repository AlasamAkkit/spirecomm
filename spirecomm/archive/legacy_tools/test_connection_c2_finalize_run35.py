from __future__ import annotations

import importlib.util
from pathlib import Path

# Finalize-only wrapper for Run 35.
#
# Run 35 was played under:
# c2-continual-teaching-v1.3.0-cumulative-policy-verified-planning
#
# Use this wrapper only after Run 35 ends to complete pending human feedback
# and post-run reflection under v1.3 while preventing Run 36 from launching.
# Do not use this file to play a new run.

# Archived historical helper: retain the original spirecomm data paths.
BASE_DIR = Path(__file__).resolve().parents[2]
V13_CONTROLLER = BASE_DIR / "test_connection_c2_continual_v1_3.py"

if not V13_CONTROLLER.is_file():
    raise FileNotFoundError(f"Missing C2 continual v1.3 controller: {V13_CONTROLLER}")

_spec = importlib.util.spec_from_file_location(
    "_c2_continual_v13_finalize35", V13_CONTROLLER,
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Could not load C2 continual v1.3 controller.")

v13 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v13)

# Preserve v1.3 controller identity and permanently cap further run starts
# in this process. The already-completed Run 35 remains eligible for
# pending reflection / feedback recovery.
v13.base.MAX_COMPLETED_RUNS = 35
v13.base.SESSION_COMPLETED_RUNS = 35


def main():
    v13.main()


if __name__ == "__main__":
    main()
