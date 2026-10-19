from __future__ import annotations

import importlib.util
from pathlib import Path

# Recovery-only wrapper used to finish Run 32's submitted human review under
# the same v1.1.1 card-prior + turn-planner architecture that played Run 32,
# without allowing Run 33 to start.
#
# Use this only after Run 32 has already produced RUN_END but
# POST_RUN_REFLECTION_COMPLETE for completed_run_number=32 is still missing.
# Once Run 32 is fully reflected and frozen, switch to the Run-33+ v1.2
# persistent-planning controller.

BASE_DIR = Path(__file__).resolve().parent
V111_CONTROLLER = BASE_DIR / "test_connection_c2_continual_v1_1_1.py"

if not V111_CONTROLLER.exists():
    raise FileNotFoundError(f"Missing C2 continual v1.1.1 controller: {V111_CONTROLLER}")

_spec = importlib.util.spec_from_file_location("_c2_continual_v111_finalize32", V111_CONTROLLER)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Could not load C2 continual v1.1.1 controller.")

v111 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v111)

# Run 32 has already ended. Capping the inherited controller here allows startup
# recovery to process the pending Run-32 reflection/human feedback, but prevents
# the main-menu router from issuing START for Run 33.
v111.v11.prior.base.MAX_COMPLETED_RUNS = 32
v111.v11.prior.base.SESSION_COMPLETED_RUNS = 32


def main():
    v111.main()


if __name__ == "__main__":
    main()
