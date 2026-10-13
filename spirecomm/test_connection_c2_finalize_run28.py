from __future__ import annotations

import importlib.util
from pathlib import Path

# Recovery-only wrapper used to finish Run 28's human review under the exact
# continual-teaching-v1.0 decision architecture without allowing Run 29 to
# start. After Run 28 is fully reflected/frozen, switch to v1.1.

BASE_DIR = Path(__file__).resolve().parent
V10_CONTROLLER = BASE_DIR / "test_connection_c2_continual_v1.py"

_spec = importlib.util.spec_from_file_location("_c2_continual_v10_freeze", V10_CONTROLLER)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Could not load continual C2 v1.0 controller.")

v10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v10)

# Run 28 has already ended. Capping the inherited controller here means startup
# recovery can complete Run 28's pending reflection, but the main-menu router
# will not issue START for Run 29.
v10.base.MAX_COMPLETED_RUNS = 28
v10.base.SESSION_COMPLETED_RUNS = 28


if __name__ == "__main__":
    v10.main()
