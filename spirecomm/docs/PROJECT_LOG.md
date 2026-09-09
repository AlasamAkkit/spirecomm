# Slay the Spire LLM Agent — Project Log

## Project objective

Build an LLM-based agent that can autonomously play Slay the Spire, evaluate how far it can progress, and later investigate whether a system that reflects on previous runs can teach the agent to improve over repeated experience.

## Core architecture

`Slay the Spire -> CommunicationMod JSON -> Python controller -> legal action generation -> LLM choice -> validated CommunicationMod command -> Slay the Spire`

Design principles established during development:

- The LLM selects only from controller-generated legal actions; arbitrary model command text is never sent directly to the game.
- Forced/deterministic interactions are handled by the controller without an LLM call.
- Controller/interface failures must be separated from LLM reasoning failures in the research analysis.
- stdout is reserved for the CommunicationMod protocol; debug/research data goes to files.
- `run_events.jsonl` is the machine-readable source of truth for runs and decisions.
- The initial baseline remains independent across runs; cross-run reflection/experience memory will be introduced as a separate experimental condition later.

## Development history

### Initial integration

- Connected Python to Slay the Spire through ModTheSpire/BaseMod/CommunicationMod.
- Verified `ready`, `start`, and `state` communication.
- Automated Ironclad Ascension 0 starts.
- Added Neow handling and map navigation.

### Early controller expansion

Live runs revealed that progressing through the game required many distinct interaction types beyond combat. Support was incrementally added for:

- card play and target selection
- end turn
- combat rewards
- card rewards and skip
- generic events
- GRID selections for upgrade/remove/transform
- rest-site actions and post-action confirmation
- merchant entry, purchasing, purge, exit, and shop-loop prevention
- chest opening and reward collection
- HAND_SELECT decisions created by cards
- multi-card sequential selection

These runs established the methodological distinction between a controller gap and an LLM reasoning gap.

### Structured research logging — v0.1.5

Introduced run IDs and `run_events.jsonl`, recording `RUN_START`, `RUN_END`, `LLM_CALL`, `ACTION`, `UNHANDLED_STATE`, and `ERROR` plus token/latency information.

### Boss reward support — v0.1.6

A live run reached the Act 1 boss chest and revealed `BOSS_REWARD` as a separate state. A dedicated LLM boss-relic decision handler was added. Later runs confirmed boss relic selection and Act 2 transition work.

### Interface audit — v0.2.0

Instead of waiting for live runs to reveal every possible screen, CommunicationMod's source was audited. The controller was expanded toward complete structural coverage of its top-level interaction types. Important additions included potions, full-slot replacement, Singing Bowl, Sapphire Key trade-offs, `GAME_OVER`, `COMPLETE`, more general GRID/HAND_SELECT handling, and corrected event option indexing.

### Performance stabilization — v0.2.1

Longer runs made the laptop progressively hot/laggy, especially with VS Code open. Raw-state logging and repeated full-state copies were reduced, normal state logs were compacted/rate-limited, diagnostic full states were separated, and a small command delay was added. Multiple subsequent runs were reported smooth with no progressive lag.

### First multi-run smoke analysis

Five completed v0.2.1 runs reached floors 16, 16, 33, 16, and 30. No `UNHANDLED_STATE` or controller `ERROR` events were observed. Live gameplay verified boss relic choices, Act 2 transition, potion use/replacement, and Sapphire Key decisions.

The smoke batch identified two remaining instrumentation/interface issues:

1. MAP actions used numeric indexes while the nodes themselves also had numeric `x` coordinates. The model sometimes returned the intended coordinate, causing the generic decoder to treat it as invalid and silently choose fallback action 0.
2. The installed CommunicationMod build omitted the documented `game_state.keys` object, leaving key ownership absent from structured logs.

### v0.2.2 — current baseline candidate

- Map choices use letters rather than numeric action indexes.
- Numeric/x-coordinate outputs can be explicitly recovered and are logged by decoder mode.
- Key ownership is tracked controller-side when CommunicationMod omits it.
- Every structured event carries an experiment tag.
- Gameplay strategy is intentionally unchanged so this version can be compared fairly with v0.2.1 and potentially frozen as the baseline.

## Next milestone

Run 5 autonomous v0.2.2 smoke games. If the controller remains error-free and the two fixes are verified, freeze the implementation as **Baseline Agent v1.0**. Only after baseline data is collected should the project introduce cross-run reflection/experience memory and compare whether the taught agent improves.
