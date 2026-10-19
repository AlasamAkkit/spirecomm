from __future__ import annotations

import importlib.util
from pathlib import Path

# Recovery/finalization only for C2 Run 36.
# Run 36 was played using v1.3.1. Preserve exactly that controller
# for its human-feedback step; never let this entry point start Run 37.
BASE_DIR = Path(__file__).resolve().parent
CONTROLLER = BASE_DIR / "test_connection_c2_continual_v1_3_1.py"
if not CONTROLLER.is_file():
    raise FileNotFoundError(f"Missing Run-36 controller: {CONTROLLER}")

_spec = importlib.util.spec_from_file_location(
    "_c2_continual_v131_finalize36", CONTROLLER
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Could not load the v1.3.1 controller.")
v131 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v131)

# Permits pending post-run feedback/reflection processing, while disallowing
# any attempt to create another C2 run from the menu router.
v131.base.MAX_COMPLETED_RUNS = 36
v131.base.SESSION_COMPLETED_RUNS = 36


def main():
    v131.main()


if __name__ == "__main__":
    main()
