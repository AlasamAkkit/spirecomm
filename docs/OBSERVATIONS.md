# Research Observations

The main rule for this file is to distinguish controller/interface limitations from genuine LLM reasoning failures.

| ID | Observation | Category | Status |
|---|---|---|---|
| OBS-001 | Generic event screens were initially unsupported. | CONTROLLER_GAP | Resolved |
| OBS-002 | High-level decisions can create secondary card-selection screens. | CONTROLLER_GAP | Resolved |
| OBS-003 | Rest sites require a separate decision interface. | CONTROLLER_GAP | Resolved |
| OBS-004 | Smith requires card selection followed by confirmation. | INTERFACE_GAP | Resolved |
| OBS-005 | Completed rest-site actions can still require `PROCEED`. | INTERFACE_GAP | Resolved |
| OBS-006 | Merchant interaction contains multiple screen states. | CONTROLLER_GAP | Resolved |
| OBS-007 | Merchant exit can produce a state-dependent re-entry loop without short-term controller memory. | MEMORY_GAP | Resolved |
| OBS-008 | Treasure rooms require a multi-stage interaction sequence. | CONTROLLER_GAP | Resolved |
| OBS-009 | Combat cards can generate nested HAND_SELECT decisions. | CONTROLLER_GAP | Resolved |
| OBS-010 | Multi-card selections must be handled sequentially across refreshed states. | INTERFACE_GAP | Resolved |
| OBS-011 | Strategic and deterministic actions should be separated to avoid unnecessary LLM calls. | EFFICIENCY | Ongoing |
| OBS-012 | Card information supplied to the LLM does not yet include complete semantic card-effect descriptions. | OBSERVATION_GAP | Open |
| OBS-013 | Boss relic rewards use a separate `BOSS_REWARD` state. | CONTROLLER_GAP | Resolved + live verified |
| OBS-014 | Terminal states can lose useful final gameplay context; evaluation needs cached state plus GAME_OVER handling. | EVALUATION_INFRASTRUCTURE | Resolved |
| OBS-015 | The early combat action space excluded potion usage, making some apparent combat failures unfair to attribute to the LLM. | ACTION_SPACE_GAP | Resolved + live verified |
| OBS-016 | Environment-interface coverage can be tested/audited separately from gameplay quality. | EVALUATION_INFRASTRUCTURE | Resolved |
| OBS-017 | Full controller coverage operated across multiple autonomous v0.2.1 runs with no logged unhandled states or controller errors. | EVALUATION_INFRASTRUCTURE | Observed |
| OBS-018 | Boss relic selection and inter-Act transition work in live gameplay. | INTERFACE_VALIDATION | Verified |
| OBS-019 | Potion use and full-slot potion replacement work in live gameplay. | INTERFACE_VALIDATION | Verified |
| OBS-020 | Numeric map action indexes are ambiguous with map `x` coordinates; the LLM sometimes returned the intended coordinate rather than the requested index. | INTERFACE_GAP | Fix implemented in v0.2.2; live verification pending |
| OBS-021 | The installed CommunicationMod build used in the smoke batch did not expose `game_state.keys`, so key acquisition succeeded in-game but was missing from structured telemetry. | OBSERVATION_GAP | Controller-side fix implemented in v0.2.2; live verification pending |

## OBS-020 — Map action representation ambiguity

During v0.2.1 smoke runs, all observed LLM fallbacks were MAP decisions. Several outputs matched a legal node's `x` coordinate but were invalid as zero-based action indexes. This could silently send the agent down a different route from the one it intended.

**v0.2.2 mitigation:** map choices are now letter-labelled. If the model nevertheless returns a unique `x` coordinate, the decoder explicitly recovers that choice and logs `decoder_mode=x_coordinate_recovery`.

**Research implication:** an apparent poor gameplay result may originate from an action-representation mismatch rather than strategic reasoning.

## OBS-021 — Key telemetry mismatch

CommunicationMod's current upstream source documents `game_state.keys = {ruby, emerald, sapphire}`, but the user's installed build produced v0.2.1 structured events where this field was absent. The game itself still accepted Sapphire Key choices.

**v0.2.2 mitigation:** the controller tracks key-producing actions (Recall, Emerald Key reward, Sapphire Key selection), commits them on the next valid in-game state, and uses the inferred state in prompts and logs. If a future CommunicationMod build provides the official key object, it remains authoritative.
