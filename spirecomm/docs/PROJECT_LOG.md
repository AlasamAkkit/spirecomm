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

### Initial integration and controller expansion

The project began by connecting Python to Slay the Spire through ModTheSpire, BaseMod, and CommunicationMod. The controller was then expanded through live runs and interface auditing to support combat, rewards, events, GRID/HAND_SELECT interactions, rest sites, shops, treasure rooms, boss relics, potions, key trade-offs, inter-Act transitions, and terminal states.

These runs established the methodological distinction between controller/interface gaps and genuine LLM reasoning failures.

### Structured logging and interface stabilization

Structured event logging was introduced for `RUN_START`, `RUN_END`, `LLM_CALL`, `ACTION`, `UNHANDLED_STATE`, and `ERROR`, together with token/latency data and experiment tags.

Important stabilization work included:

- map-choice decoding fixes;
- controller-side key tracking when the installed CommunicationMod build omitted the expected key object;
- merchant-loop prevention;
- generated-card and card-reward routing fixes;
- terminal-state caching;
- reduced state logging overhead;
- watchdog/state recovery for lost protocol responses.

### Baseline freeze — `baseline-v1.0.5`

After repeated smoke/integration testing, the gameplay controller was frozen as `baseline-v1.0.5`.

Configuration:

- model: `gpt-5.6-luna`
- character: Ironclad
- Ascension: 0
- no cross-run learning
- 30 valid completed runs
- 5-run session checkpoints

The baseline dataset is stored under:

```text
spirecomm/runs/baseline_v1_30runs_final/
```

### Condition A baseline complete

The final 30-run baseline produced:

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

The main gameplay bottleneck was mid-Act-2 attrition and risk/resource management rather than a persistent controller failure.

### Research direction refined

The project moved from the broad question of whether an LLM can improve through experience to a comparative design focused on:

- where pure self-reflection gets stuck;
- what types of mistakes it can correct autonomously;
- which failures persist despite repeated lessons;
- how human feedback changes those failure modes.

Three conditions were defined:

- **Condition A:** baseline, no cross-run learning.
- **Condition B:** pure LLM self-reflection and memory.
- **Condition C:** same learning architecture, but human curation before lessons are stored.

### Reflection mechanism — `reflection-v0.2`

The reflection pipeline was developed offline before live self-learning was enabled.

After a completed run, `reflection-v0.2`:

1. builds a compact trajectory from structured events and state summaries;
2. asks the LLM for at most three reusable lessons;
3. requires evidence points and causal reasoning;
4. applies factual/temporal verification constraints;
5. stores lessons automatically in Condition B without human semantic filtering.

Offline validation showed that the reflector can produce useful lessons, but can also generate plausible-but-imperfect or incorrect lessons. Those imperfections were preserved intentionally because reflection quality is part of the research question.

### Experience memory and retrieval

The memory bank stores structured JSONL lessons with deterministic IDs and source-run metadata.

The frozen Condition B retrieval policy is:

- exact decision category only;
- newest matching lessons first;
- maximum three lessons;
- no unrelated `GENERAL` fallback;
- no human semantic filtering;
- no prompt modification when retrieval is empty.

### Online self-reflection smoke validation

A two-run smoke test validated the complete online loop:

```text
Run 1
  -> empty memory
  -> completed run
  -> reflection
  -> append lessons
  -> reload memory
  -> Run 2 retrieves Run-1 lessons
```

The smoke test confirmed that empty memory preserves the baseline prompt, post-run reflection completes before later runs begin, memory reload works in-process, and recovery is idempotent.

### Condition B infrastructure interruption

During the real Condition B experiment, one physical run stalled at an Act 2 shop after CommunicationMod returned a valid snapshot with `ready_for_command=false` in response to a watchdog `STATE` request.

The controller had incorrectly treated receipt of any state as completion of the watchdog cycle. This disabled further polling and caused an indefinite wait.

The fix changed only protocol recovery:

- keep the watchdog active while `ready_for_command=false`;
- poll `STATE` again after the normal timeout;
- reset the watchdog only after CommunicationMod reports a command-ready state.

The interrupted physical run had no `RUN_END`, produced no reflection, and did not count toward the 30 completed Condition B runs.

### Condition B complete — 30-run pure self-reflection experiment

Condition B completed successfully with exactly:

- 30 valid `RUN_END` events;
- 30 `POST_RUN_REFLECTION_COMPLETE` events;
- 1 `EXPERIMENT_COMPLETE`;
- 85 stored lessons;
- 0 malformed memory records;
- 0 detected future-memory leakage.

Primary performance:

| Metric | Condition A | Condition B |
|---|---:|---:|
| Wins | 0/30 | 0/30 |
| Mean floor | 23.37 | **27.23** |
| Median floor | 24 | **28** |
| Best floor | 50 | 50 |
| Mean score | 200.43 | **236.63** |
| Best score | **684** | 535 |
| Reached Act 2 | 20/30 | **22/30** |
| Reached Act 3 | 1/30 | **3/30** |

Condition B progressed farther on average but still produced no win.

Important behavioural changes included:

- permanent card-reward skip rate increased from 2.8% to 14.1%;
- at campfires with HP <=40% of maximum, Condition B rested in 27/29 cases;
- the agent reached Act 3 three times;
- deaths shifted toward later boss encounters rather than only hallway/elite attrition.

The 85 lessons were concentrated in COMBAT, CARD_REWARD, EVENT, and REST categories. Many later lessons repeated variants of earlier advice, especially around low-HP survival and deck selectivity.

### Emerging interpretation after Condition B

The current evidence suggests that pure self-reflection can correct some repeated local or medium-horizon behaviours, but has a weaker effect on long-horizon planning and causal consolidation.

A particularly clear example is key planning:

- Sapphire Key ownership became common because it is an explicit local trade-off.
- No Condition B run ended with all three keys.
- All three Act 3 runs had Ruby + Sapphire but lacked Emerald.

This suggests the agent could learn the local "take the key" choice while still failing the route/planning problem required to secure the Emerald Key.

Another limitation is memory churn: the system often generated new variants of lessons it already had rather than progressively refining a coherent strategy. With newest-first retrieval and a maximum of three lessons, knowledge behaves more like a rolling recent guidance window than a consolidated long-term policy.

## Next milestone

Freeze/archive the final Condition B artifacts and design Condition C before collecting any human-feedback runs.

Condition C should preserve the actor, reflection timing, memory schema, retrieval policy, and run-level experimental controls as far as practical. The intended intervention is human review/correction of the LLM-generated reflection before lessons are stored.

The main analysis target will be:

```text
baseline/self-reflection failure
        ->
LLM reflection
        ->
human accept / correct / reject / add missing insight
        ->
stored lesson
        ->
later retrieval
        ->
behavioural outcome
```
