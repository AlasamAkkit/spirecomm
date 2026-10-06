# Slay the Spire LLM Agent — Project Log

## Project objective

Build an LLM-based agent that can autonomously play Slay the Spire and investigate how persistent reflection and human teaching affect long-horizon decision-making.

Current research question:

> To what extent can iterative human feedback improve the long-horizon decision-making of an LLM agent in Slay the Spire, compared with autonomous self-reflection under the same memory system?

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

Core design principles:

- The LLM only chooses among controller-generated legal actions.
- Arbitrary model command text is never forwarded directly to the game.
- Forced/deterministic interactions are handled without an LLM call where practical.
- Controller/interface failures are separated from gameplay reasoning failures.
- stdout is reserved for CommunicationMod protocol traffic.
- Structured JSONL events are the experimental source of truth.
- Cross-run learning occurs through external memory, not weight updates.

---

# Development chronology

## 1. CommunicationMod integration and controller expansion

The project began by connecting Python to Slay the Spire through ModTheSpire, BaseMod, and CommunicationMod.

The controller was expanded through live interface audits to support:

- combat card play and targets;
- potion use/discard/replacement;
- HAND_SELECT and GRID_SELECT;
- card rewards and combat rewards;
- ordinary events;
- shops and card removal;
- campfires and smith follow-up selection;
- treasure rooms;
- boss relics;
- map choices;
- key decisions;
- inter-Act transitions;
- GAME_OVER / terminal states.

This stage established the methodological distinction between **controller coverage** and **LLM strategic quality**.

## 2. Structured logging and robustness

Structured logging was added for events such as:

- `RUN_START`;
- `RUN_END`;
- `LLM_CALL`;
- `ACTION`;
- memory retrieval;
- API errors/recovery;
- post-run reflection;
- unhandled/error states.

Important engineering fixes included:

- map-action decoding;
- controller-side key tracking when the installed CommunicationMod omitted key telemetry;
- merchant-loop prevention;
- generated-card vs permanent-card-reward routing;
- final-state caching;
- compact state logging to reduce overhead;
- watchdog recovery for missing/non-ready state responses.

## 3. Baseline freeze — `baseline-v1.0.5`

After controller stabilization, the no-memory baseline was frozen.

Configuration:

- `gpt-5.6-luna`;
- Ironclad;
- Ascension 0;
- no cross-run memory;
- 30 valid completed runs.

Dataset:

```text
spirecomm/runs/baseline_v1_30runs_final/
```

Final baseline results:

- 0 wins;
- mean floor 23.37;
- median floor 24;
- best floor 50;
- mean score 200.43;
- best score 684;
- Act 2: 20/30;
- Act 3: 1/30.

The dominant gameplay bottleneck was mid-Act-2 attrition and resource/risk management rather than a persistent interface blocker.

## 4. Reflection-v0.2

A post-run reflector was developed and tested offline before live learning.

For each completed run it generated at most three reusable lessons, with trajectory evidence and causal reasoning requirements.

Offline validation showed a key research issue: LLM reflection can be useful while still producing plausible-but-wrong strategic conclusions, overgeneralization, or hindsight/credit-assignment errors.

Those imperfections were deliberately left uncorrected in Condition B.

## 5. Condition B — autonomous self-reflection

Condition B added online post-run reflection and a simple memory policy:

- exact decision category;
- newest lessons first;
- maximum three memories;
- no human correction;
- empty memory leaves the base actor prompt unchanged.

A two-run smoke validated the full Run 1 -> reflection -> memory -> Run 2 retrieval loop.

During official collection, one physical run stalled after CommunicationMod returned a valid but `ready_for_command=false` state to the watchdog. The watchdog was fixed to continue polling until a command-ready state appeared. The interrupted run had no completion or reflection and was excluded.

Final Condition B:

- 30 valid runs;
- 85 lessons;
- mean floor 27.23;
- median floor 28;
- mean score 236.63;
- Act 2: 22/30;
- Act 3: 3/30;
- wins: 0/30.

Behaviour changed measurably:

- permanent card-reward skip rate increased from 2.8% to 14.1%;
- at <=40% HP, B rested at 27/29 campfires;
- progression improved.

However, long-horizon planning remained weak. No run ended with all three keys, and all three Act-3 runs lacked Emerald.

The memory bank also accumulated repeated variants of similar lessons. The top-3 newest-first policy behaved more like a rolling guidance window than a stable cumulative strategy.

## 6. Condition C1 — human-curated reflection

C1 kept B's basic memory interface but inserted human review before storage.

Review actions:

- ACCEPT;
- CORRECT;
- REJECT;
- ADD.

C1 completed 30 reviewed runs and retained 73 final lessons:

- COMBAT 30;
- CARD_REWARD 17;
- REST 12;
- EVENT 8;
- SHOP 4;
- GENERAL 1;
- BOSS_REWARD 1.

Retained provenance:

- 61 accepted;
- 11 corrected;
- 1 added.

Human review corrected wrong-cause attribution, missing context, vague advice, long-horizon planning errors, and false strategic lessons.

C1 confirmed that reflection structure and reflection correctness are different problems.

## 7. B/C1 retrieval limitation identified

The B/C1 memory interface had two important limitations.

### Rolling-window loss

Only the newest three matching lessons were supplied, so older valid knowledge could disappear from active context.

### Category isolation

A lesson could contain guidance useful in several decision types but only be retrieved under its single primary category.

This motivated a follow-up in which **both** autonomous and human-taught conditions share a stronger memory architecture.

## 8. B2/C2 cumulative-playbook design

B2/C2 introduced permanent raw lesson memory plus a cumulative playbook.

Each rule contains:

- primary category;
- `applies_to`;
- `when`;
- `guidance`;
- `rationale`;
- confidence;
- `source_memory_ids`.

Every raw memory ID must remain represented by at least one rule.

The actor receives all rules applicable to the current decision category rather than only the latest three memories.

## 9. C2 smoke v0.1

The first C2 trajectory-feedback smoke validated:

```text
completed trajectory
 -> initial reflection
 -> browser human review
 -> revised final reflection
 -> permanent raw memory
 -> cumulative playbook
 -> next-run retrieval
```

The smoke exposed cross-category loss: guidance about card selectivity could be consolidated under an EVENT rule and then be unavailable at CARD_REWARD.

## 10. cumulative-playbook-v2

The playbook was upgraded with `applies_to` scopes. A rule retains one primary provenance category but can be retrieved for several decision categories.

This change was applied to both B2 and C2 so memory capacity/retrieval would not itself be the treatment difference.

## 11. C2 and B2 smoke v0.2

C2 smoke v0.2 validated:

- empty Run-1 memory;
- source coverage;
- temporal isolation;
- live cross-category retrieval;
- cumulative updates across two runs.

B2 smoke v0.2 validated the autonomous counterpart with the same architecture.

C2 smoke also exposed a stale CommunicationMod combat snapshot after Smoke Bomb. A bounded transition guard was added to both conditions. B2 smoke later exercised the same guard successfully.

## 12. B2 v1.1.0 invalidated — permanent card reward skip bug

The first official B2 cumulative-memory batch completed 15 runs, but retrospective review found a controller correctness bug.

After the actor selected Skip on a permanent card reward, CommunicationMod could keep the card reward visible on the parent reward list. The controller reopened it, causing repeated Skip -> reopen loops until a later call took a card or Singing Bowl.

Measured impact:

- 92 skip decisions;
- 19 affected reward instances;
- 9/15 runs affected;
- worst reward repeated 29 skips;
- all affected instances eventually took a card/Singing Bowl.

Because deck construction and later memory were changed, the entire batch was invalidated.

## 13. B2 v1.1.1 final control

`card-reward-skip-guard-v1` was added to remember skipped permanent reward entries within the current combat-reward flow while preserving later distinct rewards.

B2 was restarted from empty memory.

Final B2 v1.1.1:

- 15 starts / 15 completions / 15 reflections;
- seeds `260925001`...`260925015` in order;
- 0 wins;
- mean floor 18.73;
- median floor 16;
- best floor 29;
- mean score 144.60;
- best score 251;
- Act 2+: 6/15;
- Act 3: 0/15;
- 38 raw lessons;
- 14 playbook rules;
- 2,924 retrievals;
- zero current/future leakage;
- complete source coverage.

The skip guard was exercised 13 times without reopening the same declined reward, including a two-card-reward skip/advance case.

Dataset:

```text
spirecomm/runs/B2_v1_1_1_15runs_final/
```

B2 was frozen as the autonomous control.

## 14. C2 treatment simplified to authoritative human teaching

Before final C2 collection, the design was simplified.

The earlier approach let a second LLM rewrite human feedback into revised strategic lessons. This introduced a confound: outcomes reflected both the human advice and the reviser's interpretation.

Final policy `authoritative-human-teaching-v1` uses:

### APPROVE_INITIAL

Store the initial reflection lessons unchanged.

### HUMAN_TEACHING

Store the human's natural-language strategic guidance verbatim.

A metadata-only organizer may infer title, primary category, and `applies_to`, but may not rewrite strategy.

Authoritative playbook rules are regenerated deterministically from raw memory, and validation requires exact guidance equality.

## 15. C2 v1.2.0 invalidated — metadata retrieval-scope bug

The first authoritative C2 official attempt began with seed `260925001`.

Run 1 stored human teaching that explicitly discussed Neow/start-relic strategy. The teaching text was preserved correctly, but the metadata organizer omitted `GENERAL` from `applies_to`.

The controller maps `NEOW_BLESSING` to `GENERAL`, so Run 2 did not retrieve the Run-1 authoritative rule at Neow.

The rule was retrieved later in another context, demonstrating that storage and cross-run memory worked; the error was scope metadata.

The v1.2.0 attempt was invalidated.

## 16. C2 v1.2.1 scope fix and smoke

v1.2.1 added:

- explicit decision-to-retrieval-category mappings in the metadata prompt;
- a deterministic safeguard that adds `GENERAL` if authoritative human teaching explicitly mentions Neow or a starting-relic-to-boss-relic swap.

A dedicated scope smoke used isolated seeds and verified:

```text
Run 1 HUMAN_TEACHING
 -> authoritative rule contains GENERAL
 -> Run 2 NEOW_BLESSING
 -> Run-1 rule retrieved
 -> actor applies the teaching
```

The smoke passed, and v1.2.1 was frozen for official collection.

## 17. Final C2 v1.2.1 matched experiment

C2 restarted from empty official memory using the same 15 seed strings as B2 in the same order.

Final C2:

- 15 starts / 15 completions / 15 reflections;
- 0 wins;
- mean floor 27.33;
- median floor 23;
- best floor 50;
- mean score 251.47;
- median score 197;
- best score 629;
- Act 2+: 13/15;
- Act 3: 2/15;
- 25 raw lessons;
- 17 playbook rules;
- 10 HUMAN_TEACHING reviews;
- 5 APPROVE_INITIAL reviews;
- 3,705 memory retrievals;
- zero current/future leakage;
- complete source coverage;
- exact preservation of authoritative human teaching.

One transient API HTTP 500 recovered on the second attempt with no gameplay fallback.

Two actor calls returned out-of-range indexes and used the frozen deterministic index-parser fallback. These runs were retained rather than selectively rerun.

Dataset:

```text
spirecomm/runs/C2_v1_2_1_15runs_final/
```

The committed C2 archive currently contains the official event log and controller snapshots. The raw memory/playbook/reflection-output files were Git-ignored during collection and were validated separately.

## 18. Final B2 vs C2 result

| Metric | B2 | C2 |
|---|---:|---:|
| Wins | 0/15 | 0/15 |
| Mean floor | 18.73 | **27.33** |
| Median floor | 16 | **23** |
| Best floor | 29 | **50** |
| Mean score | 144.60 | **251.47** |
| Median score | 112 | **197** |
| Best score | 251 | **629** |
| Act 2+ | 6/15 | **13/15** |
| Act 3 | 0/15 | **2/15** |

Paired matched-seed comparison:

- floor: C2 better on 11/15, B2 better on 4/15;
- mean paired floor difference: +8.60;
- score: C2 better on 10/15, B2 better on 5/15;
- mean paired score difference: +106.87.

The result supports the claim that authoritative human teaching improves survival and long-horizon progression relative to autonomous reflection under the same cumulative-memory system.

It does **not** support claiming that the task is solved: both conditions achieved 0 wins.

## 19. Architecture selected for continuation

B2 has completed its role as the autonomous control.

C2 is the architecture selected for the remainder of the project.

The next research stage should:

1. continue C2 learning on fresh unseen training seeds;
2. keep human review enabled during learning;
3. freeze controller + raw memory + playbook after the learning phase;
4. evaluate on a separate held-out set of unseen seeds;
5. disable feedback, reflection updates, and memory writes during held-out evaluation.

This separates **learning** from **generalization evaluation** and prevents test trajectories from becoming additional training examples.
