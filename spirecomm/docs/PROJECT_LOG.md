# Slay the Spire LLM Agent — Project Log

## Project objective

Build an LLM-based agent that can autonomously play Slay the Spire and investigate whether it can improve through cross-run learning from its own experience. The current research focus is:

> Where are the limits of self-reflective learning in an LLM game-playing agent, and how does human feedback help overcome those limits?

## Core architecture

```text
Slay the Spire
  -> CommunicationMod JSON
  -> Python controller
  -> legal action generation
  -> LLM actor
  -> validated CommunicationMod command
  -> Slay the Spire
```

Design principles:

- The LLM chooses only from controller-generated legal actions.
- Arbitrary model command text is never sent directly to the game.
- Forced/deterministic interactions are handled without an LLM call where practical.
- Controller/interface failures are separated from genuine reasoning failures.
- stdout is reserved for the CommunicationMod protocol; research/debug output goes to files.
- Structured JSONL events are the machine-readable source of truth for experiments.

## Development history

### Initial integration

- Connected Python to Slay the Spire through ModTheSpire, BaseMod, and CommunicationMod.
- Verified `ready`, `start`, and `state` communication.
- Automated Ironclad Ascension 0 starts.
- Added Neow handling and map navigation.

### Controller expansion

Live runs revealed that progressing through the game required many interaction types beyond combat. Support was added for:

- card play and target selection
- end turn
- combat rewards
- card rewards and skip
- generic events
- GRID selections for upgrade/remove/transform
- rest-site actions and confirmation
- merchant entry, purchasing, purge, exit, and shop-loop prevention
- chest opening and reward collection
- HAND_SELECT decisions created by cards
- multi-card sequential selection
- boss relic rewards
- potions and potion replacement
- Sapphire Key trade-offs
- deterministic proceed/confirm states
- inter-Act transitions and terminal-state handling

These runs established the methodological distinction between controller gaps and LLM reasoning gaps.

### Structured logging

Run IDs and structured JSONL logging were introduced for:

- `RUN_START`
- `RUN_END`
- `LLM_CALL`
- `ACTION`
- `UNHANDLED_STATE`
- `ERROR`

Token use, latency, legal actions, selected actions, and experiment tags are logged for later analysis.

### Interface stabilization

An audit of CommunicationMod's top-level state/action interface was used to reduce the chance of discovering critical states only during long autonomous runs. Important fixes included:

- full combat reward handling
- boss reward handling
- GRID and HAND_SELECT coverage
- merchant loop prevention
- event option indexing
- potion actions/replacement
- terminal-state caching
- map decoder fixes using letter-labelled choices
- controller-side key tracking when the installed CommunicationMod build omitted `game_state.keys`

### Baseline freeze — `baseline-v1.0.5`

After repeated smoke/integration testing, the controller was frozen as `baseline-v1.0.5` for the main baseline experiment.

The final baseline configuration used:

- model: `gpt-5.6-luna`
- character: Ironclad
- Ascension: 0
- no cross-run learning
- 30 valid completed runs
- 5-run session checkpoints

The baseline dataset is stored at:

```text
spirecomm/runs/baseline_v1_30runs_final/
```

### Baseline experiment complete

The 30-run baseline produced:

- 0 wins
- mean floor: 23.37
- median floor: 24
- best floor: 50
- mean score: 200.43
- best score: 684
- Act 2 reached: 20/30 (66.7%)
- Act 3 reached: 1/30 (3.3%)
- 6,798 LLM calls
- 7,663,520 combined input/output tokens
- mean LLM latency: 6.85 s

The most important strategic bottleneck was mid-Act-2 attrition and risk/resource management rather than a persistent controller failure.

### Research direction refined

The project moved from the broad question of whether an LLM can improve through experience to a comparative design focused on:

- where pure self-reflection gets stuck;
- what types of mistakes it can correct autonomously;
- what types of human corrections are needed to overcome those limits.

Three conditions were defined:

- **Condition A:** baseline, no cross-run learning.
- **Condition B:** pure LLM self-reflection and memory.
- **Condition C:** same reflection/memory architecture, but human curation before storage.

### Reflection mechanism development

The reflection pipeline was developed offline before modifying live gameplay.

The final frozen reflector version is `reflection-v0.2`. After a completed run it:

1. builds a compact trajectory from structured events and compact state logs;
2. asks the LLM for at most three reusable lessons;
3. requires evidence points and causal reasoning;
4. includes safeguards against unsupported card counts, temporal-state mistakes, generated-card confusion, and illegal combat counterfactuals;
5. stores lessons without human semantic filtering in Condition B.

Offline testing on previously unseen baseline runs showed that the reflector can produce useful lessons, but can also generate plausible-but-imperfect or clearly wrong lessons. This is treated as part of the research signal rather than manually corrected in Condition B.

### Experience memory and retrieval

A structured JSONL memory format was introduced. Each lesson stores:

- deterministic memory ID
- source run
- category
- title
- situation
- reusable lesson
- evidence points
- reasoning
- confidence

Retrieval was deliberately kept simple and interpretable:

- exact decision category only;
- newest matching lessons first;
- maximum three lessons;
- no semantic human filtering;
- no prompt modification when no relevant memory exists.

### Online self-reflection smoke test

A two-run online smoke test validated the complete loop:

```text
Run 1
  -> empty memory / baseline-equivalent prompts
  -> completed run
  -> post-run reflection
  -> lessons appended
  -> memory reloaded
  -> Run 2 retrieves Run-1 lessons
```

The smoke test confirmed:

- empty memory leaves the baseline prompt unchanged;
- retrieved memory IDs/categories match the decision category;
- Run 2 uses only lessons from prior completed runs;
- post-run reflection is crash-recoverable and idempotent;
- failures in reflection pause the experiment rather than silently starting the next run with stale memory.

### Condition B implementation

The final Condition B controller is designed for 30 completed runs with 5-run checkpoints. It starts with a fresh empty `reflection/memory.jsonl`, runs `reflection-v0.2` after every completed run, and makes later decisions using at most three matching lessons.

The learning mechanism is frozen for the full Condition B experiment. Human acceptance/rejection/editing of lessons is not allowed in this condition.

## Next milestone

Collect the 30-run Condition B dataset without modifying the actor/controller/reflection/retrieval policy unless a genuine infrastructure bug makes the experiment invalid.

After Condition B is complete, implement Condition C using the same architecture and controls, with human curation as the intended experimental difference.
