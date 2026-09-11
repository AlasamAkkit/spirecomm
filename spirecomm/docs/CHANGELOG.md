# Changelog

## self-reflection-condition-b-v1.0.0 — Condition B experiment build

### Added

- Online post-run reflection after every completed run using frozen `reflection-v0.2`.
- Persistent JSONL experience memory for cross-run learning.
- Deterministic lesson IDs tied to the completed source run.
- Category-based memory retrieval with a maximum of three lessons.
- `MEMORY_RETRIEVAL`, `POST_RUN_REFLECTION_START`, `POST_RUN_REFLECTION_COMPLETE`, and post-run reflection failure telemetry.
- Immediate in-process memory reload so Run N+1 can use lessons generated after Run N.
- Crash recovery for completed runs that have not yet produced a completed reflection.
- Experiment-integrity checks for stale memory, mismatched run IDs, duplicate lesson IDs, and missing reflection completions.
- Condition B-specific runtime files and 5-run session checkpoints.

### Experimental controls

- Run 1 starts with empty memory.
- Empty retrieval leaves the actor prompt unchanged from the baseline prompt.
- No human semantic filtering, rejection, or editing is allowed in Condition B.
- Reflection frequency is once per completed run.
- Retrieval is exact-category only, newest first, maximum three lessons.

### Validation

- Two-run online smoke test confirmed the complete loop: empty-memory Run 1 -> post-run reflection -> persistent memory -> Run 2 retrieval.
- Memory IDs/categories matched requested decision categories in the smoke run.
- Generated-card choices in active combat are routed to COMBAT rather than permanent CARD_REWARD memory.
- Neow and specialist decision categories no longer receive unrelated fallback memories.

## reflection-v0.2 — Reflection quality/verification build

### Added

- Evidence-backed lesson generation with at most three lessons per trajectory.
- Required `evidence_points`, `reasoning`, and confidence fields.
- Explicit checks for temporal-state mistakes in combat.
- Combat recommendations must be legal at the cited state.
- Exact card/deck counts must be supported by the final build.
- Generated combat cards are separated from permanent deck additions.
- Map lessons respect incomplete route-topology logging.
- Unsupported counterfactuals must be framed cautiously and assigned lower confidence.

### Research decision

- Semantic errors in otherwise valid self-generated lessons are intentionally not manually removed in Condition B; autonomous reflection quality is part of the experiment.

## Memory retrieval prototype

### Added

- Structured JSONL memory schema.
- Deterministic memory IDs such as `self_run_14_01`.
- Exact-category retrieval and prompt formatting.
- Maximum retrieval size of three lessons.
- Development scripts for building and inspecting prototype memory.

### Changed

- Removed automatic `GENERAL` fallback when a specialist category already exists or when an unrelated specialist category is empty.
- Empty memory no longer adds a synthetic "no relevant memories" block to the actor prompt.

## baseline-v1.0.5 — Final baseline freeze

### Fixed

- Route handling so normal combat logic is not incorrectly applied to stale post-combat/card-reward states.
- Additional controller/interface edge cases discovered during long autonomous runs.

### Experiment configuration

- Model: `gpt-5.6-luna`
- Character: Ironclad
- Ascension: 0
- 30 completed runs
- 5-run session checkpoints
- No cross-run learning

### Result

- Final Condition A baseline dataset completed and frozen under `spirecomm/runs/baseline_v1_30runs_final/`.

## v0.2.2 — Baseline candidate smoke build

### Fixed

- Removed numeric ambiguity from map decisions. Map options are letter-labelled while actual `x=` coordinates remain visible.
- Added explicit recovery when the LLM returns an `x` coordinate instead of the requested letter.
- Added `decoder_mode` to MAP `LLM_CALL` events.
- Added controller-side Ruby/Emerald/Sapphire key tracking for CommunicationMod builds that omit the documented key object.
- Added `KEY_TRACK_UPDATE` events.

### Strategy changes

- None. This release intentionally changed interface decoding/telemetry only.

## v0.2.1 — Performance/stability build

- Reduced raw-state logging to compact, rate-limited summaries.
- Added `state_dumps.jsonl` for diagnostic full states.
- Removed repeated full-state `deepcopy()` calls.
- Added small command pacing delay to reduce sustained load.
- Preserved structured `run_events.jsonl` logging.

## v0.2.0 — Interface coverage build

- Audited CommunicationMod's top-level state/action interface.
- Added/expanded potions, potion replacement, Sapphire Key trade-offs, Singing Bowl, campfire options, `COMPLETE`, and `GAME_OVER`.
- Improved generic GRID and HAND_SELECT handling.
- Corrected disabled-event option mapping.
- Added cached final-state information for run-end evaluation.
- Refactored toward centralized state routing and legal-action generation.

## v0.1.6 — Boss reward build

- Added `BOSS_REWARD` handling and boss-relic selection.

## v0.1.5 — Structured logging build

- Added run IDs and `run_events.jsonl`.
- Added `RUN_START`, `RUN_END`, `LLM_CALL`, `ACTION`, `UNHANDLED_STATE`, and `ERROR` events.
- Added token and latency logging.

## Pre-v0.1.5 — Incremental controller development

The initial agent was expanded from a basic CommunicationMod connection to support Neow, map routing, combat, rewards, generic events, GRID selection, rest sites, shops, chest/relic collection, HAND_SELECT, and deterministic proceed/confirm states.
