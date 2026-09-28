# B2/C2 Follow-up v1.1

## Change from v1.0
The cumulative playbook now supports cross-category applicability.
Each playbook rule has a primary category plus `applies_to`, e.g. a lesson learned from an EVENT can also apply to CARD_REWARD decisions.
This fixes the smoke-v0.1 finding where human feedback about skipping cards was consolidated into an EVENT rule and was therefore invisible during CARD_REWARD decisions.

## C2 smoke v0.2
1. Copy `reflection/followup_reflection.py` and `reflection/feedback_app.py` into the project reflection folder.
2. Copy `spirecomm/test_connection_c2_smoke_v0_2.py` into the spirecomm folder and copy it over `test_connection.py`.
3. Start feedback UI:
   `python .\reflection\feedback_app.py --output-dir .\reflection\condition_c2_outputs_smoke_v02`
4. Start STS through ModTheSpire.
5. Complete feedback for both runs.

The v0.2 smoke uses separate files from v0.1, so the successful v0.1 smoke artifacts can be kept untouched.

Expected C2 smoke-v0.2 files:
- `spirecomm/run_events_c2_smoke_v02.jsonl`
- `reflection/condition_c2_raw_memory_smoke_v02.jsonl`
- `reflection/condition_c2_playbook_smoke_v02.json`
- `reflection/condition_c2_feedback_smoke_v02.jsonl`
- `reflection/condition_c2_outputs_smoke_v02/`

## Official matched experiment
Do not start until smoke v0.2 is verified.
- B2 controller: `test_connection_b2_v1_1_0.py`
- C2 controller: `test_connection_c2_v1_1_0.py`
- Both use the same 15 seed strings in the same order.
- Both use cumulative playbook v2 and cross-category `applies_to` retrieval.
- Only C2 receives human trajectory feedback before final reflection.
