# Changelog

## B2 smoke v0.2 — matched self-reflection validation

### Result

- Completed two valid B2 smoke runs.
- Run 1: loss, Act 2 Floor 33, score 302.
- Run 2: loss, Act 1 Floor 16, score 104.
- Stored six raw self-reflection lessons.
- Final cumulative playbook contained seven rules and was updated through Run 2.
- Complete raw-memory source coverage verified.
- No current/future-run memory leakage detected.
- Live cross-category retrieval verified.

### Smoke Bomb guard validation

- Run 2 exercised the new transition guard after Smoke Bomb.
- Five stale combat snapshots were handled with bounded waits.
- The controller then detected a clean `COMBAT_REWARD` transition.
- Zero CommunicationMod errors were recorded.

### Experimental status

Both C2 and B2 smoke v0.2 now pass. The v1.1 pair is ready for official matched 15-seed collection.

## Smoke Bomb transition guard — pre-official B2/C2 hotfix

### Fixed

- Detected a stale post-Smoke-Bomb combat snapshot during C2 smoke v0.2.
- The game had begun leaving combat, but CommunicationMod briefly still reported `screen_type=NONE`, `room_phase=COMBAT`, and combat commands as available.
- The controller could therefore make another LLM combat decision and issue `PLAY` after the foreground screen had already advanced to `COMBAT_REWARD`.

### Guard

- Mark a pending escape when the selected potion action is Smoke Bomb.
- While the foreground state remains the stale combat shape, issue bounded transition waits rather than another tactical LLM call.
- Clear the guard immediately once the game leaves the combat foreground.
- Release the guard after five waits if the transition does not complete, preventing deadlock.
- Applied identically to B2/C2 smoke v0.2 and official v1.1 controllers.

### Experimental impact

- The two invalid-command errors in C2 smoke Run 2 did not prevent run completion, post-run reflection, memory update, or playbook update.
- The hotfix was applied before official B2/C2 data collection.

## C2 smoke v0.2 — cumulative-playbook-v2 validation

### Result

- Completed two valid C2 smoke runs.
- Run 1: loss, Act 2 Floor 25, score 236.
- Run 2: loss, Act 3 Floor 38, score 454.
- Stored six final human-guided lessons.
- Final playbook contained six rules and `updated_through_run = 2`.
- Complete raw-memory source coverage verified.
- No current/future-run memory leakage detected.
- Live cross-category retrieval verified through a REST-primary rule retrieved during MAP decisions.

### Human-feedback validation

- Run 1 human feedback corrected the initial reflector's causal emphasis: smithing at 39/56 HP was not treated as automatically wrong, while the earlier Bite/max-HP trade without Blood Vial became the higher-priority lesson.
- Run 2 feedback retained the initial reflection while adding a stronger deck-size/selectivity guideline.

## B2/C2 v1.1 — cumulative-playbook-v2 and cross-category retrieval

### Changed

- Added `applies_to` metadata to cumulative playbook rules.
- Retrieval now scans the complete playbook and returns every rule applicable to the current decision category.
- A rule can retain one primary category for provenance while influencing several relevant decision types.
- Playbook validation preserves raw-memory source coverage while validating `applies_to`.
- Updated B2/C2 smoke controllers to v0.2 and official controllers to v1.1.

### Motivation

C2 smoke v0.1 showed that human feedback about card selectivity could be consolidated into an EVENT rule and therefore be invisible during a later CARD_REWARD decision. v1.1 fixes this memory-interface problem for both B2 and C2.

### Experimental control

- Official B2 and C2 use the same 15 seed strings in the same order.
- Both use the same cumulative-playbook-v2 implementation.
- The intended treatment difference is C2's trajectory-level human feedback before final reflection.

## C2 smoke v0.1 — trajectory-feedback validation

### Added

- Browser-based trajectory review through `reflection/feedback_app.py`.
- Run summary, automatic review candidates, strategic timeline, full compact trajectory, and initial reflection display.
- Natural-language human feedback instead of manual structured lesson editing.
- Human-guided reflection revision before final lesson storage.
- Permanent raw lesson memory and cumulative playbook update.

### Validation

- Completed two smoke runs.
- Run 1 feedback was converted into reusable final lessons.
- Run 2 retrieved only prior-run knowledge.
- No current/future-run memory was required for the smoke learning loop.

### Finding

- Single-category playbook retrieval was insufficient for lessons whose guidance spans several decision types.
- This finding motivated cumulative-playbook-v2 and `applies_to`.

## B2/C2 follow-up memory architecture

### Added

- Permanent raw lesson banks for B2 and C2.
- Cumulative playbook consolidation instead of newest-three lesson retrieval.
- `source_memory_ids` provenance on every playbook rule.
- Validation requiring every raw lesson ID to remain covered by the playbook.
- Idempotent playbook reuse when a completed run has already been consolidated.
- Matched official seed list `260925001` through `260925015`.
- Separate smoke and official files so development runs cannot contaminate official memory.

### Research decision

B2 and C2 share the improved memory interface. This allows the follow-up to test the effect of human feedback without giving C2 a larger memory capacity or a different gameplay controller.

## Condition C1 completion — 30-run human-curated dataset

### Result

- Completed 30 human-reviewed runs.
- Retained 73 final curated lessons.
- Retained lesson categories:
  - COMBAT: 30
  - CARD_REWARD: 17
  - REST: 12
  - EVENT: 8
  - SHOP: 4
  - GENERAL: 1
  - BOSS_REWARD: 1
- Retained-memory provenance records contain 61 accepted lessons, 11 corrected lessons, and 1 human-added lesson.

### Research finding

Human review corrected strategically meaningful issues including wrong-cause attribution, missed contextual information, vague advice, long-horizon planning errors, and false lessons.

### Limitation retained from Condition B

C1 still used newest-first, exact-category, maximum-three retrieval. A corrected lesson could therefore be stored successfully yet fail to appear in a later relevant decision.

## Condition B completion — 30-run self-reflection dataset

### Result

- Completed 30 valid self-reflection runs.
- Produced 85 stored lessons.
- Recorded 30 `POST_RUN_REFLECTION_COMPLETE` events.
- Recorded 0 detected future-memory leakage.
- Mean floor increased from 23.37 (Condition A) to 27.23.
- Median floor increased from 24 to 28.
- Mean score increased from 200.43 to 236.63.
- Act 3 reach rate increased from 1/30 to 3/30.
- Wins remained 0/30.

### Behavioural findings

- Permanent card-reward skip rate increased from 2.8% to 14.1%.
- At <=40% max HP, the agent rested at 27/29 campfires.
- Sapphire Key acquisition became common, but all-three-key completion remained 0/30.
- Memory repeatedly regenerated variants of similar local lessons, exposing limited lesson consolidation.

## Condition B watchdog recovery patch

### Fixed

- Corrected a protocol deadlock where a watchdog `STATE` request returned a valid state with `ready_for_command=false`.
- The controller previously cleared the watchdog as soon as any state arrived, then waited indefinitely because no command could be issued.
- The watchdog now remains active until CommunicationMod explicitly reports `ready_for_command=true`.

### Experimental impact

- One physical Condition B run was interrupted.
- The interrupted run had no `RUN_END`, produced no reflection, and was excluded automatically.
- The first 10 completed runs and all later completed runs remained part of the same Condition B experiment.

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

- Removed numeric ambiguity from map decisions.
- Added explicit recovery when the LLM returns an `x` coordinate instead of the requested letter.
- Added `decoder_mode` to MAP `LLM_CALL` events.
- Added controller-side Ruby/Emerald/Sapphire key tracking.
- Added `KEY_TRACK_UPDATE` events.

## v0.2.1 — Performance/stability build

- Reduced raw state logging to compact, rate-limited summaries.
- Added `state_dumps.jsonl` for diagnostic full states.
- Removed repeated full-state `deepcopy()` calls.
- Added small command pacing delay.
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
