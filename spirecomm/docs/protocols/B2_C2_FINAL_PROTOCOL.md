# B2/C2 Final Matched Follow-up Protocol

> **Status:** COMPLETE / FROZEN  
> **Canonical controlled-experiment protocol.** This document describes the final matched B2/C2 experiment. Later continual-C2 work is documented separately in `C2_CONTINUAL_TEACHING_PROTOCOL.md`.

## 1. Research question

The matched follow-up tests whether **authoritative human teaching** improves an LLM Slay the Spire agent beyond autonomous self-reflection when both conditions share the same cumulative external-memory architecture.

- **B2 v1.1.1 — autonomous control:** completed trajectory → autonomous LLM reflection → permanent raw memory → cumulative playbook.
- **C2 v1.2.1 — human-taught treatment:** completed trajectory → initial LLM reflection → human review → approved lessons unchanged OR verbatim human teaching → the same cumulative memory/playbook mechanism.

The actor model, character, Ascension level, gameplay interface, official seed order, and cumulative memory mechanism were aligned. The intended treatment difference was the authoritative human-review path in C2.

## 2. Why the follow-up was needed

The earlier B/C1 study used newest-first exact-category retrieval capped at three lessons. This created two important limitations:

1. **Rolling-window loss:** older useful lessons could stop influencing behavior as newer same-category lessons arrived.
2. **Category isolation:** a lesson could contain guidance relevant to several decision types but be retrievable only through its single primary category.

B2/C2 therefore used `cumulative-playbook-v2`.

Every final lesson is retained in raw memory. Playbook rules contain:

- primary category;
- `applies_to`;
- `when`;
- `guidance`;
- `rationale`;
- confidence;
- `source_memory_ids`.

Every raw lesson ID must remain represented by at least one playbook rule.

## 3. Final conditions

### B2 v1.1.1 — autonomous self-reflection

```text
completed run
 -> compact trajectory
 -> LLM reflection
 -> final lessons
 -> permanent raw memory
 -> cumulative playbook
 -> later decisions
```

No human semantic correction is allowed.

### C2 v1.2.1 — authoritative human teaching

```text
completed run
 -> compact trajectory
 -> initial LLM reflection
 -> human review
      -> APPROVE_INITIAL
           -> initial lessons stored unchanged
      OR
      -> HUMAN_TEACHING
           -> exact human strategic text stored verbatim
           -> metadata-only indexing
 -> permanent raw memory
 -> cumulative playbook
 -> later decisions
```

For `HUMAN_TEACHING`, an LLM may infer only a neutral title, one primary category, and `applies_to` categories. It may not paraphrase, summarize, correct, soften, expand, or otherwise rewrite strategic content.

Authoritative teaching is excluded from LLM strategic consolidation and is deterministically reattached to the actor-facing playbook. Validation requires actor-facing guidance to equal the stored human text exactly.

Policy identifier:

```text
authoritative-human-teaching-v1
```

## 4. Matched controls

Both final conditions used:

- model: `gpt-5.6-luna`;
- character: Ironclad;
- Ascension 0;
- identical official seed order;
- identical legal-action interface;
- identical cumulative-playbook-v2 retrieval;
- isolated condition-specific memory/log files;
- reflection completion before the next run could start;
- the same controller correctness guards.

Official seeds, in order:

```text
260925001
260925002
260925003
260925004
260925005
260925006
260925007
260925008
260925009
260925010
260925011
260925012
260925013
260925014
260925015
```

The order matters because memory accumulates sequentially.

## 5. Invalidated development batches

### B2 v1.1.0 — card-reward skip bug

The first official B2 cumulative-memory batch completed 15 runs but was invalidated because a skipped permanent card reward could reappear from the parent `COMBAT_REWARD` list.

Measured impact:

- 92 skip decisions;
- 19 affected reward instances;
- 9 affected runs;
- worst case: 29 repeated skips;
- every affected instance eventually took a card or Singing Bowl.

Archive:

```text
spirecomm/runs/B2_v1_1_0_invalidated_card_skip_bug/
```

The v1.1.1 `card-reward-skip-guard-v1` fixed the issue and B2 was restarted from empty memory.

### C2 v1.2.0 — metadata scope bug

Run-1 authoritative teaching discussed Neow/start-relic strategy, but the metadata organizer omitted `GENERAL` from `applies_to`. Because `NEOW_BLESSING -> GENERAL`, Run 2 did not retrieve the lesson at Neow.

Archive:

```text
spirecomm/runs/C2_v1_2_0_invalidated_metadata_scope_bug/
```

C2 v1.2.1 added explicit retrieval-category mappings plus a deterministic `GENERAL` safeguard for Neow/start-relic teaching. The dedicated scope smoke passed before official collection resumed.

## 6. Final B2 v1.1.1 control

Dataset:

```text
spirecomm/runs/B2_v1_1_1_15runs_final/
```

| Metric | B2 v1.1.1 |
|---|---:|
| Runs | 15 |
| Wins | 0 |
| Mean floor | 18.73 |
| Median floor | 16 |
| Best floor | 29 |
| Mean score | 144.60 |
| Median score | 112 |
| Best score | 251 |
| Reached Act 2+ | 6/15 |
| Reached Act 3 | 0/15 |
| Raw lessons | 38 |
| Final playbook rules | 14 |

Integrity checks:

- exactly 15 starts, 15 completions, and 15 post-run reflections;
- exact official seed order;
- Run 1 had empty memory;
- 2,924 memory retrievals;
- zero detected current/future memory leakage;
- complete raw-memory source coverage;
- 13 permanent card skips with no same-reward reopen loop.

## 7. Final C2 v1.2.1 treatment

Dataset:

```text
spirecomm/runs/C2_v1_2_1_15runs_final/
```

| Metric | C2 v1.2.1 |
|---|---:|
| Runs | 15 |
| Wins | 0 |
| Mean floor | 27.33 |
| Median floor | 23 |
| Best floor | 50 |
| Mean score | 251.47 |
| Median score | 197 |
| Best score | 629 |
| Reached Act 2+ | 13/15 |
| Reached Act 3 | 2/15 |
| Raw lessons | 25 |
| Final playbook rules | 17 |

Human review distribution:

- `HUMAN_TEACHING`: 10 runs;
- `APPROVE_INITIAL`: 5 runs.

Integrity checks:

- exactly 15 starts, 15 completions, and 15 post-run reflections;
- exact official seed order;
- 3,705 memory retrievals;
- zero detected current/future memory leakage;
- complete raw-memory source coverage;
- all authoritative human teaching preserved verbatim through actor-facing guidance.

Runtime caveats retained in the official dataset:

- one transient HTTP 500 in Run 6 recovered on retry;
- two out-of-range LLM indexes used the frozen deterministic parser fallback.

## 8. Matched comparison

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
| Act 2+ | 6/15 | **13/15** |
| Act 3 | 0/15 | **2/15** |

Paired direction:

- floor: C2 better on 11/15 seeds; B2 better on 4/15; mean paired gain `+8.60` floors;
- score: C2 better on 10/15 seeds; B2 better on 5/15; mean paired gain `+106.87` points.

The supported conclusion is:

> Under the matched cumulative-memory follow-up, authoritative human teaching improved survival depth and long-horizon progression relative to autonomous self-reflection.

Neither system won, so this is evidence of improved progression rather than solved gameplay.

See `../FINAL_B2_C2_ANALYSIS.md` for the consolidated controlled-phase analysis.

## 9. Source-of-truth rule

Final controlled-phase analysis uses only:

```text
spirecomm/runs/B2_v1_1_1_15runs_final/
spirecomm/runs/C2_v1_2_1_15runs_final/
```

Do not mix smoke runs, interrupted attempts, invalidated B2/C2 batches, or later continual-C2 runs into the matched analysis.

The structured event log is the machine-readable source of truth for run outcomes and runtime decisions.

## 10. Historical note on the next phase

The original protocol proposed extended C2 learning followed by a frozen held-out evaluation. That proposal was **superseded** after the matched experiment. The project instead moved to an open-ended continual human-teaching phase with fresh random seeds, persistent C2 memory, and explicit controller-version intervention boundaries.

The active longitudinal protocol is:

```text
docs/protocols/C2_CONTINUAL_TEACHING_PROTOCOL.md
```
