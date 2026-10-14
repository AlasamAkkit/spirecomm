# Final B2 vs C2 Matched Analysis

> **Status:** COMPLETE / FROZEN CONTROLLED ANALYSIS.  
> Later continual-C2 runs and controller interventions are intentionally excluded from this comparison.

## Purpose

This document records the final controlled comparison between:

- **B2 v1.1.1** — autonomous self-reflection with cumulative memory; and
- **C2 v1.2.1** — the same cumulative-memory gameplay architecture plus authoritative human review.

The comparison asks whether human teaching improves long-horizon Slay the Spire decision-making beyond autonomous self-reflection when both conditions share the same actor, legal-action interface, memory system, character, Ascension level, and seed sequence.

## Experimental controls

Both final conditions used:

- model: `gpt-5.6-luna`;
- character: Ironclad;
- Ascension 0;
- 15 official seed strings `260925001` through `260925015`, in the same order;
- the same legal-action/controller interface;
- `cumulative-playbook-v2`;
- the same Smoke Bomb transition guard;
- the same permanent card-reward skip guard;
- isolated condition-specific memory/logs;
- reflection/memory completion before a later run could start.

Treatment difference:

- **B2:** autonomous LLM reflection supplies final lessons;
- **C2:** human review follows the initial reflection and ends as either `APPROVE_INITIAL` or authoritative verbatim `HUMAN_TEACHING`.

## Final datasets

### B2 v1.1.1

```text
spirecomm/runs/B2_v1_1_1_15runs_final/
```

Integrity:

- 15 valid starts and completions;
- 15 post-run reflections;
- 38 raw lessons;
- 14 final playbook rules;
- 2,924 memory retrievals;
- zero detected current/future memory leakage;
- complete raw-memory source coverage;
- card-reward skip guard live-validated.

### C2 v1.2.1

```text
spirecomm/runs/C2_v1_2_1_15runs_final/
```

Integrity:

- 15 valid starts and completions;
- 15 post-run reflections;
- 25 raw lessons;
- 17 final playbook rules;
- 3,705 memory retrievals;
- zero detected current/future memory leakage;
- complete raw-memory source coverage;
- 10 `HUMAN_TEACHING` and 5 `APPROVE_INITIAL` reviews;
- authoritative human teaching preserved verbatim through raw memory and actor-facing playbook guidance.

Runtime caveats retained rather than selectively rerun:

- one transient HTTP 500 recovered on retry;
- two out-of-range LLM action indexes used the frozen deterministic parser fallback.

## Aggregate results

| Metric | B2 v1.1.1 | C2 v1.2.1 |
|---|---:|---:|
| Runs | 15 | 15 |
| Wins | 0 | 0 |
| Mean floor | 18.73 | **27.33** |
| Median floor | 16 | **23** |
| Best floor | 29 | **50** |
| Mean score | 144.60 | **251.47** |
| Median score | 112 | **197** |
| Best score | 251 | **629** |
| Reached Act 2+ | 6/15 | **13/15** |
| Reached Act 3 | 0/15 | **2/15** |

C2 improved every reported progression/score aggregate except wins, which remained 0 in both conditions.

## Matched-seed direction

Floor:

- C2 > B2 on 11/15 matched seeds;
- B2 > C2 on 4/15;
- ties: 0;
- mean paired difference: **+8.60 floors for C2**.

Score:

- C2 > B2 on 10/15 matched seeds;
- B2 > C2 on 5/15;
- mean paired difference: **+106.87 points for C2**.

Because memory accumulates sequentially, this is a comparison of two matched learning trajectories over the same ordered seed schedule rather than fifteen independent memoryless trials.

## Interpretation

The strongest supported conclusion is:

> Under the matched cumulative-memory follow-up, authoritative human teaching substantially improved survival depth and long-horizon progression relative to autonomous self-reflection.

The result should not be overstated:

- neither condition won;
- the sample is 15 sequential learning runs per condition;
- memory content differs over time because each condition learns from its own earlier trajectories;
- the experiment demonstrates improved progression, not solved gameplay or universal generalization.

## What changed behaviorally

The broader project already showed that autonomous reflection can alter local/medium-horizon behavior. In the initial B condition, card skipping increased substantially relative to baseline and low-HP campfire behavior became more conservative.

The B2/C2 follow-up asks a different question: with the stronger cumulative-memory interface held shared, does authoritative human teaching provide additional value?

C2's substantially better Act-2/Act-3 progression supports that claim. Human review can correct strategic content that an autonomous reflector may misattribute, omit, or overgeneralize.

## Memory-quality interpretation

C2 did not simply accumulate more raw lessons than B2. At the end of the matched experiment:

- B2 had 38 raw lessons / 14 playbook rules;
- C2 had 25 raw lessons / 17 playbook rules.

The treatment therefore should not be described as “more memory wins.” The important difference is the **source and quality of strategic teaching** under the same external-memory mechanism.

## Human-teaching attribution

The final C2 design intentionally removed a second strategic LLM that had previously rewritten human feedback.

For `HUMAN_TEACHING`:

- human text is stored verbatim;
- only retrieval metadata may be inferred automatically;
- the playbook reattaches authoritative guidance deterministically;
- validation checks exact preservation.

This makes the treatment closer to direct human instruction rather than human feedback filtered through another model's strategic rewrite.

## Important invalidated batches

### B2 v1.1.0

Invalidated because skipped permanent card rewards could reopen while CommunicationMod continued exposing them on the parent reward list.

Measured impact:

- 92 repeated skip decisions;
- 19 affected reward instances;
- 9 affected runs;
- worst affected instance: 29 repeated skips.

Because this changed permanent deck construction and later learning, B2 was restarted from empty memory with v1.1.1.

### C2 v1.2.0

Invalidated because Run-1 human teaching about Neow was stored correctly but metadata omitted `GENERAL`, so Run 2 failed to retrieve the lesson at `NEOW_BLESSING`.

C2 v1.2.1 added explicit decision/retrieval-category mapping plus a deterministic Neow/start-relic scope safeguard. A dedicated smoke verified the corrected cross-run retrieval path before final collection.

## Relation to A / B / C1

```text
A: no cross-run learning
  -> baseline

B: autonomous reflection + top-3 exact-category memory
  -> changes some local behavior
  -> exposes memory churn/category isolation

C1: human-curated reflection + same top-3 memory
  -> shows value of human semantic correction
  -> still limited by retrieval interface

B2: autonomous reflection + cumulative playbook
  -> stronger-memory control

C2: authoritative human teaching + same cumulative playbook
  -> final matched human-teaching treatment
```

This sequence separates two questions:

1. Can autonomous reflection change behavior? — A vs B.
2. Does human teaching add value beyond autonomous reflection under the same stronger memory architecture? — B2 vs C2.

## Analysis boundary

Only the final B2 and C2 archives above belong in this matched analysis.

Do not add:

- smoke runs;
- invalidated B2/C2 batches;
- continual C2 Runs 16+;
- later card-prior, sticky-planning, or focused-memory interventions.

Those later continual runs answer a different exploratory question and use changing controller architectures.

## Subsequent research direction

At the time the matched analysis first completed, the proposed next step was additional C2 training followed by a frozen held-out evaluation.

That proposal was later **superseded** by the open-ended continual-C2 design. The project now follows one continuously taught agent across fresh seeds, Ascension milestones, and explicit architecture interventions.

Current continual records:

```text
CONTINUAL_C2_STATUS.md
CONTROLLER_HISTORY.md
protocols/C2_CONTINUAL_TEACHING_PROTOCOL.md
```

This supersession does not change any result or interpretation in the frozen B2/C2 comparison above.
