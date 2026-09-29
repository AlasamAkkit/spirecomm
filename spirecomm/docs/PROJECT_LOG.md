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

## Condition C1 — 30-run human-curated reflection experiment

Condition C1 was implemented after the completed Condition B study to examine whether direct human correction could address weaknesses in autonomous reflection.

The gameplay controller and run-level reflection timing remained aligned with Condition B. The key intervention occurred **after the LLM reflection and before memory storage**.

For each completed run:

```text
completed trajectory
    -> reflection-v0.2
    -> human review
         ACCEPT
         CORRECT
         REJECT
         ADD
    -> final curated lessons
    -> memory
    -> later retrieval
```

The review workflow preserved the original trajectory and initial LLM reflection so that human intervention could be attributed explicitly rather than silently editing the dataset.

Condition C1 completed 30 reviewed runs. The final memory bank contains **73 retained human-curated lessons**:

| Category | Retained lessons |
|---|---:|
| COMBAT | 30 |
| CARD_REWARD | 17 |
| REST | 12 |
| EVENT | 8 |
| SHOP | 4 |
| GENERAL | 1 |
| BOSS_REWARD | 1 |

Among those retained final lessons, provenance records show:

- 61 accepted LLM lessons;
- 11 corrected lessons;
- 1 human-added lesson.

Corrections include examples of wrong-cause attribution, missed strategic context, over-vague survival advice, long-horizon planning issues, and false lessons. Rejected lessons are not represented in the retained final-memory count.

The C1 workflow confirmed an important part of the research premise: an LLM reflection can be structurally valid and evidence-backed while still requiring strategic correction from a human reviewer.

## Limitation exposed by B/C1 memory retrieval

The completed B/C1 experiments used a simple retrieval policy:

- map the current decision to one category;
- retrieve newest matching lessons;
- cap retrieval at three lessons.

This was intentionally easy to audit, but the completed studies exposed two limitations.

### Rolling-window loss

Older lessons can stop influencing gameplay because only the newest three matching memories are supplied. The memory bank therefore behaves more like a rolling guidance window than a cumulative strategy.

### Category isolation

A lesson may contain advice useful to several decision types but still be stored under only one category. Exact-category retrieval can then make part of that lesson unavailable where it matters.

These limitations complicate interpretation of the original B vs C1 comparison: a high-quality human correction can be stored correctly yet fail to reach a later decision because of the memory interface rather than because the advice itself was ineffective.

## B2/C2 follow-up design

A follow-up experiment was therefore created to isolate the value of human feedback while improving the shared memory mechanism for **both** conditions.

### B2 — improved self-reflection

```text
trajectory
    -> LLM reflection
    -> final lessons
    -> permanent raw memory
    -> cumulative playbook
    -> future decisions
```

### C2 — human-guided reflection

```text
trajectory
    -> initial LLM reflection
    -> human trajectory-level feedback
    -> LLM revised reflection
    -> final lessons
    -> permanent raw memory
    -> same cumulative playbook
    -> future decisions
```

Unlike C1, C2 does not require the human to edit individual structured lesson fields. A browser UI presents:

- run outcome/build summary;
- automatically flagged review candidates;
- the strategic timeline;
- the complete compact trajectory;
- the initial LLM reflection.

The reviewer writes one natural-language response describing what the initial reflection missed or misunderstood. If the reflection is already adequate, the reviewer records an explicit “initial reflection looks right” judgement.

This keeps the human intervention closer to **trajectory interpretation and causal feedback** rather than manual JSON editing.

## Cumulative playbook architecture

The B2/C2 follow-up replaces newest-three retrieval with a cumulative playbook.

Every final lesson is permanently retained in raw JSONL memory. An LLM consolidator maintains a compact playbook whose rules contain:

- one primary category;
- `applies_to` decision categories;
- `when`;
- `guidance`;
- `rationale`;
- confidence;
- the contributing `source_memory_ids`.

The playbook validator enforces a coverage invariant:

> Every raw memory ID must remain represented by at least one playbook rule.

A playbook update is rejected and retried if consolidation drops raw-memory coverage.

The actor retrieves **all rules applicable to the current decision category**, rather than selecting only the newest three memories.

## C2 smoke v0.1

A two-run C2 smoke test validated the new trajectory-level feedback loop.

Run 1 human feedback included several distinct strategic points, including:

- normally avoiding the Bite/max-HP trade without the Blood Vial interaction;
- becoming more selective with card rewards once the deck is established;
- sequencing Armaments+ early;
- building toward a coherent deck plan;
- avoiding low-value shop routing/spending.

The feedback successfully produced revised final lessons, permanent raw memory, and an updated cumulative playbook. Run 2 then retrieved knowledge originating only from the prior completed run, confirming temporal isolation.

However, the smoke test revealed an important retrieval flaw. A consolidated rule can contain guidance relevant to another decision category while being stored only under its primary category. For example, deck-selectivity advice learned while reviewing an EVENT could be invisible during a later CARD_REWARD decision.

## B2/C2 v1.1 — cross-category playbook

The follow-up architecture was revised to **cumulative-playbook-v2**.

Each rule now includes an `applies_to` list. Retrieval scans the full playbook and returns every rule whose scope contains the current category, or whose scope is GENERAL.

Example:

```json
{
  "category": "EVENT",
  "applies_to": ["EVENT", "CARD_REWARD"],
  "guidance": "..."
}
```

This preserves the rule's primary provenance while allowing the strategic idea to transfer to every decision type where it is relevant.

The official B2 and C2 v1.1 controllers are deliberately almost identical. They use:

- the same actor model: `gpt-5.6-luna`;
- Ironclad;
- Ascension 0;
- the same legal-action controller;
- the same cumulative-memory implementation;
- the same 15 fixed seed strings in the same order;
- five-run session checkpoints.

The intended treatment difference is only:

- **B2:** the initial self-reflection becomes final memory;
- **C2:** human trajectory feedback is used to revise the reflection before final memory.

## Follow-up experiment safeguards

The v1.1 controller preserves the earlier experimental protections and adds cumulative-memory integrity checking.

Important safeguards include:

- no gameplay fallback after exhausted API retries;
- infrastructure-interrupted attempts do not count as completed experimental runs;
- `RUN_END` is written before post-run reflection;
- a later run cannot start until the previous completed run's reflection/memory update succeeds;
- startup recovery processes completed-but-unreflected runs before gameplay;
- raw-memory IDs are checked against source run IDs;
- every raw-memory ID must remain covered by the playbook;
- `updated_through_run` must match the latest completed run;
- smoke and official memory/output files are isolated;
- B2 and C2 official conditions use matched seeds.

## C2 smoke v0.2 — playbook-v2 validation

The two-run C2 smoke v0.2 completed with the v1.1 follow-up memory design.

Validated properties:

- exactly two valid `RUN_END` events and two completed post-run reflections;
- Run 1 started with empty follow-up memory;
- Run 1 produced three final human-guided lessons;
- Run 2 used only lessons originating from Run 1;
- no current-run or future-run lesson was retrieved during Run 2;
- the final raw-memory bank contained six lessons;
- `cumulative-playbook-v2` updated through Run 2;
- every raw memory ID remained covered by at least one playbook rule;
- cross-category retrieval occurred in live gameplay.

A concrete cross-category example occurred when `pb_rest_01`, whose primary category is REST, was retrieved during MAP decisions because its `applies_to` scope included MAP. This confirms that the v1.1 fix is not merely serialized metadata; the actor retrieval path actually uses it.

### Smoke-v0.2 controller transition finding

Run 2 also exposed a separate CommunicationMod timing edge case after the actor used Smoke Bomb in an elite combat.

CommunicationMod briefly returned a command-ready stale combat snapshot while the game was already transitioning out of combat. The controller interpreted that stale snapshot as a new tactical decision, issued another `PLAY`, and CommunicationMod later rejected it because the foreground state had become `COMBAT_REWARD`.

The run recovered automatically and completed normally, so this did not invalidate the memory-system findings. However, official collection should not contain avoidable invalid-command noise.

A narrow controller hotfix was therefore added to all B2/C2 smoke and official controllers:

- selecting Smoke Bomb marks a pending combat-escape transition;
- stale `NONE + COMBAT` snapshots are temporarily handled with bounded `WAIT 30`/state recovery rather than another LLM tactical decision;
- the guard clears as soon as the foreground state leaves combat;
- after five unsuccessful waits it releases and resumes normal routing, preventing a permanent deadlock.

This patch changes transition handling only; it does not change the B2/C2 memory treatment or decision prompts.

## B2 smoke v0.2 — matched self-reflection validation

B2 smoke v0.2 completed two runs using the same cumulative-playbook-v2 design as C2 but without human trajectory feedback.

Validated properties:

- Run 1 began with no learned memory;
- Run 1 produced three self-reflection lessons and five consolidated playbook rules;
- Run 2 retrieved only Run-1 memory;
- no current/future-run leakage occurred;
- six raw lessons were retained after Run 2;
- the final playbook contained seven rules with full raw-memory source coverage;
- live cross-category retrieval occurred in MAP, COMBAT, CARD_REWARD, REST, and EVENT contexts.

The previously added Smoke Bomb transition guard was exercised during Run 2 and worked as intended: five stale combat snapshots were handled with bounded waits, followed by a clean transition to COMBAT_REWARD and zero CommunicationMod command errors.

The official B2/C2 v1.1 controllers were re-compared after the hotfix. They have identical line counts and differ only in 18 condition-identity/output-path/status lines, preserving the intended matched treatment design.

## Current milestone — v1.1 validation before official collection

The repository now contains:

```text
spirecomm/test_connection_b2_smoke_v0_2.py
spirecomm/test_connection_c2_smoke_v0_2.py
spirecomm/test_connection_b2_v1_1_0.py
spirecomm/test_connection_c2_v1_1_0.py
reflection/followup_reflection.py
reflection/feedback_app.py
spirecomm/FOLLOWUP_B2_C2_V1_1_PROTOCOL.md
```

The next experimental sequence is:

1. **C2 smoke v0.2 — complete**;
2. **B2 smoke v0.2 — complete**;
3. freeze the matched v1.1 build;
4. run official B2 and C2 with the same 15 seeds, beginning with B2;
5. analyse aggregate and paired seed-by-seed outcomes.

The official analysis should include performance outcomes together with behavioural and memory-system measures, especially whether human feedback changes credit assignment, long-horizon planning, deck selectivity, resource management, and the persistence/application of learned rules.
