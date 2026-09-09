# Changelog

## v0.2.2 — Baseline candidate smoke build

### Fixed
- Removed numeric ambiguity from map decisions. Map options are now labelled with letters (`A`, `B`, `C`, ...), while the actual `x=` coordinates remain visible in the descriptions.
- Added explicit recovery when the LLM still returns an `x` coordinate instead of a letter. A unique coordinate is mapped back to the intended legal action rather than silently falling back to action 0.
- Added `decoder_mode` to MAP `LLM_CALL` events so normal letter outputs, recovered coordinates, and true fallbacks can be distinguished.
- Added controller-side Ruby/Emerald/Sapphire key tracking for CommunicationMod builds that omit the documented `game_state.keys` object.
- Added `KEY_TRACK_UPDATE` events when inferred key acquisition is committed on the next valid game state.
- `RUN_END.final_keys` and normal event `keys` now use effective key state even when the wire state omits keys.

### Added
- `EXPERIMENT_TAG = "baseline_candidate_smoke"` to every structured event for easier batch filtering.

### Strategy changes
- None. This release intentionally changes interface decoding/telemetry only, not gameplay strategy.

## v0.2.1 — Performance/stability build

- Reduced raw state logging from full pretty-printed JSON on every update to compact, rate-limited summaries.
- Added `state_dumps.jsonl` for full diagnostic states only when unusual conditions occur.
- Removed repeated full-state `deepcopy()` calls.
- Added a small command pacing delay to reduce sustained Java/Python load.
- Preserved structured `run_events.jsonl` logging.
- Result: multi-run testing became smooth enough to run repeatedly without the earlier progressive lag.

## v0.2.0 — Interface coverage build

- Audited CommunicationMod's top-level screen/action interface instead of discovering screens only through live play.
- Added/expanded handling for potions, potion replacement, Sapphire Key trade-offs, Singing Bowl, all base campfire options, `COMPLETE`, and `GAME_OVER`.
- Improved generic GRID and HAND_SELECT handling.
- Corrected disabled-event option mapping using CommunicationMod `choice_index` semantics.
- Added cached final-state information for run-end evaluation.
- Refactored the agent toward a centralized state router and legal-action generation model.

## v0.1.6 — Boss reward build

- Added `BOSS_REWARD` handling.
- Added LLM selection among boss relics and skip.
- Later live runs confirmed boss relic selection and transition to Act 2 work.

## v0.1.5 — Structured logging build

- Added run IDs and `run_events.jsonl`.
- Added `RUN_START`, `RUN_END`, `LLM_CALL`, `ACTION`, `UNHANDLED_STATE`, and `ERROR` event types.
- Added token and latency logging for LLM calls.

## Pre-v0.1.5 — Incremental controller development

The initial agent was expanded iteratively from a basic CommunicationMod connection to support:

- Neow interaction
- map routing
- combat card play and end turn
- combat rewards
- card rewards
- generic events
- GRID card selection
- rest sites
- shops
- chest opening/relic collection
- HAND_SELECT
- deterministic proceed/confirm states
