from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTROLLER = ROOT / "test_connection_c2_continual_v1_3_1.py"
spec = importlib.util.spec_from_file_location("_c2_v131_block_test", CONTROLLER)
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load v1.3.1 controller")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

assert module.INTERVENTION_START_RUN == 36
assert module.PREVIOUS_COMPLETED_RUN == 35
assert module.MEMORY_POLICY == "all_applicable_rules_no_topk_with_context_pinning_v1"
assert module.v130.v121.v120.v112.v111.v11.prior.base.STSAgent is module.ContinualC2V131Agent

turn35 = [
    "Play Reckless Charge on Torch Head (10 HP)",
    "Play Shrug It Off+",
    "Play Impervious",
    "Play Defend+",
]
frail_player = {
    "block": 0,
    "powers": [{"id": "Frail", "name": "Frail", "amount": 1}],
}
frail = module.project_simple_block(frail_player, turn35)
assert frail["frail_active"]
assert [x["effective"] for x in frail["card_details"]] == [8, 22, 6]
assert frail["known_projected_block"] == 36
assert "Reckless Charge" not in frail["unmodelled_played_cards"]
assert module._card_name("Play Reckless Charge on Torch Head (10 HP)") == "Reckless Charge"

normal = module.project_simple_block({"block": 0, "powers": []}, turn35)
assert normal["known_projected_block"] == 49
dex = module.project_simple_block({
    "block": 3,
    "powers": [
        {"id": "Frail", "amount": 1},
        {"id": "Dexterity", "amount": 2},
    ],
}, ["Play Defend+", "Play Impervious"])
assert dex["known_projected_block"] == 3 + 7 + 24, dex
unknown = module.project_simple_block(frail_player, ["Play Entrench"])
assert unknown["unmodelled_played_cards"] == ["Entrench"]

print("PASS: v1.3.1 entrypoint is bound to ContinualC2V131Agent")
print("PASS: cumulative memory policy is unchanged")
print("PASS: Frail Run-35 example: printed 49 -> effective 36")
print("PASS: no-Frail example: printed 49 -> effective 49")
print("PASS: Dexterity + Frail per-card rounding")
print("PASS: targeted-card parsing and unknown-effect reporting")
