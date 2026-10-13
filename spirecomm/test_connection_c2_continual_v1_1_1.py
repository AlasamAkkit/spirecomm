from __future__ import annotations

import importlib.util
from pathlib import Path

# ============================================================
# C2 CONTINUAL TEACHING v1.1.1 ACTIVATION HOTFIX
# ============================================================
#
# v1.1 introduced the intended Run-29 intervention:
#   - fixed expert Ironclad card-quality priors for permanent card rewards;
#   - explicit contextual scoring of every reward option, including Skip;
#   - whole-turn combat planning before selecting the first legal action.
#
# The v1.1 module correctly defines ContinualC2V11Agent, but its inherited
# CommunicationMod main loop still points base.STSAgent at the v1.0 class.
# This thin wrapper fixes only that class binding. No gameplay prompt, memory,
# feedback, seed, Ascension, card-prior, or turn-planning logic is changed.
#
# Intervention boundary:
#   Runs 16-28: c2-continual-teaching-v1.0
#   Run 29 onward: c2-continual-teaching-v1.1.1-card-prior-turn-planner

CONTROLLER_VERSION = "c2-continual-teaching-v1.1.1-card-prior-turn-planner"

BASE_DIR = Path(__file__).resolve().parent
V11_CONTROLLER = BASE_DIR / "test_connection_c2_continual_v1_1.py"

if not V11_CONTROLLER.exists():
    raise FileNotFoundError(f"Missing C2 continual v1.1 controller: {V11_CONTROLLER}")

_spec = importlib.util.spec_from_file_location("_c2_continual_v11", V11_CONTROLLER)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Could not load C2 continual v1.1 controller.")

v11 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v11)

# Make both metadata layers report the hotfixed controller version.
v11.CONTINUAL_CONTROLLER_VERSION = CONTROLLER_VERSION
v11.prior.CONTINUAL_CONTROLLER_VERSION = CONTROLLER_VERSION

# Critical activation fix: prior.main() delegates to the frozen base.main(),
# which constructs base.STSAgent. Point that symbol at the v1.1 subclass.
v11.prior.ContinualC2Agent = v11.ContinualC2V11Agent
v11.prior.base.STSAgent = v11.ContinualC2V11Agent


def main():
    v11.prior.main()


if __name__ == "__main__":
    main()
