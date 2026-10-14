from __future__ import annotations

import importlib.util
from pathlib import Path

# Recovery/finalize-only wrapper for Run 34.
#
# Run 34 was played under
# c2-continual-teaching-v1.2.1-applicability-recency-hotfix.
# This wrapper loads that exact controller so pending human review and post-run
# reflection are finalized under the same provenance, while capping the
# experiment at 34 completed runs so Run 35 cannot start accidentally.
#
# After POST_RUN_REFLECTION_COMPLETE reaches completed_run_number=34, close the
# game/controller, freeze the Run-34 checkpoint, and switch to the next
# architecture only after its preflight passes.

BASE_DIR = Path(__file__).resolve().parent
V121_CONTROLLER = BASE_DIR / "test_connection_c2_continual_v1_2_1.py"

if not V121_CONTROLLER.exists():
    raise FileNotFoundError(
        f"Missing C2 continual v1.2.1 controller: {V121_CONTROLLER}"
    )

_spec = importlib.util.spec_from_file_location(
    "_c2_continual_v121_finalize34",
    V121_CONTROLLER,
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Could not load C2 continual v1.2.1 controller.")

v121 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v121)

# Run 34 has already ended. Capping the inherited base controller permits
# startup recovery / human-review processing for Run 34 but prevents the main
# menu router from issuing START for Run 35.
v121.base.MAX_COMPLETED_RUNS = 34
v121.base.SESSION_COMPLETED_RUNS = 34


def main():
    v121.main()


if __name__ == "__main__":
    main()
