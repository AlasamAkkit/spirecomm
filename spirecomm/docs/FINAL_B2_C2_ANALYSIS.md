# Final B2 vs C2 Matched Analysis

## Purpose

This document records the final controlled comparison between:

- **B2 v1.1.1** — autonomous self-reflection with cumulative memory; and
- **C2 v1.2.1** — the same cumulative-memory gameplay architecture plus authoritative human review.

The comparison asks whether human teaching improves long-horizon Slay the Spire decision-making beyond autonomous self-reflection when both conditions share the same actor, legal-action interface, memory capacity, retrieval mechanism, character, Ascension level, and seed sequence.

## Experimental controls

Both final conditions used:

- model: `gpt-5.6-luna`;
- character: Ironclad;
- Ascension: 0;
- 15 official seed strings, `260925001` through `260925015`, in the same order;
- the same legal-action/controller interface;
- the same cumulative-playbook-v2 memory mechanism;
- the same Smoke Bomb transition guard;
- the same permanent card-reward skip guard;
- isolated condition-specific memory and logs;
- reflection/memory completion before a later run could start.

The treatment difference was the source of final lessons:

- **B2:** autonomous LLM reflection;
- **C2:** human review after the initial reflection, using either `APPROVE_INITIAL` or authoritative verbatim `HUMAN_TEACHING`.

## Final datasets

### B2 v1.1.1

Archive:

```text
spirecomm/runs/B2_v1_1_1_15runs_final/
```

Final integrity:

- 15 valid starts and 15 completions;
- 15 post-run reflections;
- 38 raw lessons;
- 14 final playbook rules;
- 2,924 memory retrievals;
- zero detected current-run or future-run leakage;
- complete raw-memory source coverage;
- permanent card-reward skip guard live-validated.

### C2 v1.2.1

Archive:

```text
spirecomm/runs/C2_v1_2_1_15runs_final/
```

Final integrity:

- 15 starts and 15 completions;
- 15 post-run reflections;
- 25 raw lessons;
- 17 final playbook rules;
- 3,705 memory retrievals;
- zero detected current-run or future-run leakage;
- complete raw-memory source coverage;
- 10 `HUMAN_TEACHING` reviews;
- 5 `APPROVE_INITIAL` reviews;
- all authoritative human teaching preserved verbatim in actor-facing guidance.

The committed Git archive currently contains the official C2 event log and controller snapshots. Raw C2 memory/playbook/reflection outputs were Git-ignored during collection and were separately validated during the final audit.

## Performance results

| Metric | B2 v1.1.1 | C2 v1.2.1 | Difference |
|---|---:|---:|---:|
| Runs | 15 | 15 | — |
| Wins | 0 | 0 | 0 |
| Mean floor | 18.73 | **27.33** | **+8.60** |
| Median floor | 16 | **23** | +7 |
| Best floor | 29 | **50** | +21 |
| Mean score | 144.60 | **251.47** | **+106.87** |
| Median score | 112 | **197** | +85 |
| Best score | 251 | **629** | +378 |
| Reached Act 2+ | 6/15 | **13/15** | +7 runs |
| Reached Act 3 | 0/15 | **2/15** | +2 runs |

Neither condition won a run.

## Paired matched-seed result

Because both conditions used the same seeds in the same order, the primary descriptive comparison can be made per matched seed.

### Floor reached

- C2 higher than B2: **11/15 seeds**.
- B2 higher than C2: **4/15 seeds**.
- Ties: 0.
- Mean paired difference: **+8.60 floors for C2**.

### Score

- C2 higher than B2: **10/15 seeds**.
- B2 higher than C2: **5/15 seeds**.
- Ties: 0.
- Mean paired difference: **+106.87 points for C2**.

These results are reported descriptively because the sample contains only 15 matched runs and the sequential memory process means later runs are not fully independent observations.

## Main interpretation

The clearest difference is **survival depth**.

B2 reached Act 2 or beyond on 6/15 seeds. C2 did so on 13/15. B2 never reached Act 3; C2 reached Act 3 twice, with both runs reaching floor 50.

This suggests that authoritative human teaching helped the agent avoid enough early- and mid-run strategic mistakes to expose it to later-game states more consistently.

The result should not be overstated. C2 still achieved 0/15 wins, so the evidence supports improved progression rather than solved gameplay.

A suitable conclusion is:

> Under a matched 15-seed follow-up using the same cumulative-memory architecture, authoritative human teaching substantially improved average progression and score relative to autonomous self-reflection, especially by reducing early-game failures and enabling Act-3 play. However, neither system achieved a win, so long-horizon planning and end-game competence remain unresolved.

## Why C2 is considered the architecture to carry forward

B2 was included as a control, not as a separate long-term product direction. Its purpose was to determine whether improvements in the cumulative-memory system could be explained by autonomous reflection alone.

C2 produced materially stronger descriptive performance under the same matched seed sequence. Therefore the project proceeds with C2-style authoritative human teaching for the next learning phase.

## C2 teaching behavior

Final C2 review distribution:

- `HUMAN_TEACHING`: 10 runs;
- `APPROVE_INITIAL`: 5 runs.

Authoritative teaching was stored verbatim. The metadata-only organizer could infer only:

- title;
- primary category;
- `applies_to`.

It could not rewrite strategy.

Recurring strategic themes in the final C2 memory/playbook included:

- committing to a coherent deck plan rather than accumulating unrelated cards;
- skipping cards that do not contribute to the plan;
- HP conservation and healing decisions;
- balancing damage dealt against damage taken;
- route planning and elite/boss preparation;
- appropriate use of block and potions;
- avoiding incompatible or redundant deck strategies.

## Integrity caveats

### Transient API error

One C2 gameplay call received an API HTTP 500 on its first attempt. The controller retried and recovered on attempt 2. No heuristic gameplay action was substituted, so the run remains valid.

### Invalid-index actor outputs

Two C2 LLM calls returned an out-of-range action index and triggered the controller's deterministic index fallback:

1. Run 3, Act 1 floor 13: two event options existed, but the actor returned index `2`; fallback selected index 0, taking 175 gold plus Doubt.
2. Run 7, Act 3 floor 35: legal choices were Offering+ or End Turn, but the actor returned index `2`; fallback selected End Turn.

These are retained as model-output/protocol failures rather than removed after observing outcomes. They occurred in 2 of 3,705 C2 LLM decision calls (about 0.054%).

### No wins

The strongest limitation is that both B2 and C2 produced zero wins. The comparison therefore demonstrates improved progression, not task completion.

### Small sequential sample

Fifteen runs per condition is a small sample. In addition, cross-run memory makes the sequence path-dependent: Run 1 affects the knowledge available in Run 2, and so on. The matched seed order helps control environmental randomness, but later observations are not independent in the same way as ordinary i.i.d. test samples.

## Important invalidated batches

### B2 v1.1.0

Invalidated because a skipped permanent card reward could reopen while CommunicationMod continued exposing it on the parent reward list.

Measured impact:

- 92 repeated skip decisions;
- 19 affected reward instances;
- 9 affected runs;
- all affected instances eventually resolved by taking a card or Singing Bowl.

Because the bug altered deck construction and therefore later learning, B2 was restarted from empty memory with v1.1.1.

### C2 v1.2.0

Invalidated because Run-1 human teaching about Neow was stored correctly but the metadata organizer omitted the `GENERAL` scope. Run 2 therefore failed to retrieve that teaching at `NEOW_BLESSING`.

C2 v1.2.1 added:

- explicit mapping between controller decisions and retrieval categories; and
- a deterministic safeguard adding `GENERAL` for explicit Neow/start-relic-to-boss-relic teaching.

A dedicated scope smoke confirmed the corrected Run-1 -> Run-2 Neow retrieval path before final C2 collection.

## Relation to the earlier A/B/C1 study

The project progression is:

```text
A: no cross-run learning
  -> establishes baseline

B: autonomous reflection + top-3 exact-category memory
  -> improves some local behavior
  -> exposes memory churn / category isolation

C1: human-curated reflection + same top-3 memory
  -> validates value of human semantic correction
  -> still limited by retrieval interface

B2: autonomous reflection + cumulative playbook
  -> control for improved memory architecture

C2: authoritative human teaching + same cumulative playbook
  -> final matched human-teaching treatment
```

This sequence separates two questions:

1. Can autonomous reflection help at all? — addressed by A vs B.
2. Does human teaching add value beyond autonomous reflection under the same stronger memory architecture? — addressed by B2 vs C2.

## Next phase

The matched comparison is complete. The next phase should not reuse the same 15 seeds for continued learning.

Recommended design:

```text
C2 v1.2.1 learned state
    -> continue human-guided learning on fresh training seeds
    -> accumulate additional teaching
    -> freeze controller + raw memory + playbook
    -> disable feedback/reflection updates
    -> evaluate on held-out unseen seeds
```

The held-out evaluation should use seeds never used in the learning phase. This provides a cleaner test of whether the accumulated human-taught strategy generalizes to unseen runs rather than merely improving on trajectories that participated in learning.
