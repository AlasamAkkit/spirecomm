from __future__ import annotations

import importlib.util
from pathlib import Path

# Recovery/finalize-only wrapper for Run 33.
#
# Run 33 was played under c2-continual-teaching-v1.2.0-persistent-planning.
# This wrapper loads that exact controller so the pending human review and
# post-run reflection are finalized under the same provenance, while capping
# the experiment at 33 completed runs so Run 34 cannot start accidentally.
#
# After POST_RUN_REFLECTION_COMPLETE reaches completed_run_number=33, close the
# game/controller and switch test_connection.py to the Run-34+ v1.2.1 memory-
# retrieval hotfix before starting another run.

BASE_DIR = Path(__file__).resolve().parent
V12_CONTROLLER = BASE_DIR / "test_connection_c2_continual_v1_2.py"

if not V12_CONTROLLER.exists():
    raise FileNotFoundError(f"Missing C2 continual v1.2.0 controller: {V12_CONTROLLER}")

_spec = importlib.util.spec_from_file_location("_c2_continual_v12_finalize33", V12_CONTROLLER)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Could not load C2 continual v1.2.0 controller.")

v12 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v12)

# Run 33 has already ended. Capping the inherited continual controller allows
# startup recovery / human-review processing for Run 33, but prevents the main
# menu router from issuing START for Run 34.
base = v12.v112.v111.v11.prior.base
base.MAX_COMPLETED_RUNS = 33
base.SESSION_COMPLETED_RUNS = 33


def main():
    v12.main()


if __name__ == "__main__":
    main()
