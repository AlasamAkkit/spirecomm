# B2/C2 Final Follow-up Protocol

## Purpose

The B2/C2 follow-up tests whether **authoritative human teaching** improves an LLM Slay the Spire agent beyond autonomous self-reflection when both conditions share the same cumulative memory system.

- **B2 v1.1.1 — autonomous control:** completed trajectory -> autonomous LLM reflection -> permanent raw memory -> cumulative playbook.
- **C2 v1.2.1 — human-taught treatment:** completed trajectory -> initial LLM reflection -> human review -> approved lessons unchanged OR verbatim human teaching -> same cumulative memory/playbook.

The actor model, character, Ascension level, gameplay controller, legal-action interface, official seed order, and memory mechanism are aligned. The intended treatment difference is the authoritative human-review path in C2.

**Status: FINAL MATCHED EXPERIMENT COMPLETE.**

---

# 1. Why the follow-up was needed

The earlier B/C1 study used newest-first exact-category retrieval capped at three lessons.

Two limitations emerged:

1. **Rolling-window loss** — older useful lessons could stop influencing behavior as newer same-category lessons arrived.
2. **Category isolation** — one lesson could contain guidance relevant to several decision types but be retrievable only through its single primary category.

B2/C2 therefore use `cumulative-playbook-v2`.

Every final lesson is retained permanently in raw memory. Playbook rules include:

- primary category;
- `applies_to`;
- `when`;
- `guidance`;
- `rationale`;
- confidence;
- `source_memory_ids`.

Every raw lesson ID must remain represented by at least one playbook rule. Gameplay retrieval scans the complete playbook and injects every rule applicable to the current decision category.

---

# 2. Final condition definitions

## B2 v1.1.1

Autonomous self-reflection control.

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

## C2 v1.2.1

Authoritative human-taught treatment.

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

For `HUMAN_TEACHING`, an LLM may infer only:

- a short neutral title;
- one primary category;
- `applies_to` categories.

It may **not** paraphrase, summarize, correct, soften, expand, or rewrite strategic content.

Authoritative human teaching is excluded from LLM strategic consolidation. Its playbook rule is reconstructed deterministically from raw memory, and validation requires actor-facing guidance to equal the stored human text exactly.

Policy identifier:

```text
authoritative-human-teaching-v1
```

---

# 3. Matched experimental controls

Both final conditions used:

- model: `gpt-5.6-luna`;
- character: Ironclad;
- Ascension: 0;
- identical official seed order;
- identical legal-action interface;
- identical cumulative-playbook-v2 retrieval;
- isolated condition-specific memory/log files;
- reflection completion before the next run could start;
- the same controller correctness guards.

Official seed sequence:

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

The same order matters because memory accumulates sequentially: earlier runs determine what knowledge is available in later runs.

---

# 4. Pre-official validation

## C2 smoke v0.1

Validated the trajectory-level human-feedback loop but exposed cross-category retrieval loss.

## C2 smoke v0.2

Validated cumulative-playbook-v2, full source coverage, temporal isolation, and live cross-category retrieval.

Also exposed a stale post-Smoke-Bomb combat snapshot.

## B2 smoke v0.2

Validated the autonomous counterpart and successfully exercised the Smoke Bomb transition guard.

### Smoke Bomb guard

Selecting Smoke Bomb marks a pending escape transition. Bounded stale combat snapshots are suppressed until the foreground leaves combat, preventing invalid post-combat tactical commands.

---

# 5. B2 v1.1.0 invalidation

The first official B2 cumulative-memory batch completed 15 runs but is **invalidated**.

## Bug

After a permanent card reward was skipped, CommunicationMod could continue exposing the same card entry on the parent `COMBAT_REWARD` list. The controller reopened it, producing repeated Skip -> reopen loops.

## Measured impact

- 92 skip decisions;
- 19 affected reward instances;
- 9 affected completed runs;
- worst instance: 29 repeated skips;
- all affected instances eventually took a card or Singing Bowl.

Because permanent deck construction was altered, downstream trajectories and learned memory were contaminated.

Archive:

```text
spirecomm/runs/B2_v1_1_0_invalidated_card_skip_bug/
```

## v1.1.1 fix

`card-reward-skip-guard-v1` tracks skipped permanent reward entries within the current reward flow. The same declined entry is never reopened, while later distinct card rewards remain available.

B2 was restarted from empty memory.

---

# 6. Final B2 v1.1.1 control

**Status: COMPLETE / FROZEN**

Dataset:

```text
spirecomm/runs/B2_v1_1_1_15runs_final/
```

## Results

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

## Integrity

- exactly 15 starts and 15 completions;
- 15 post-run reflections;
- exact official seed order;
- Run 1 empty memory;
- 2,924 memory retrievals;
- zero current/future memory leakage;
- every raw lesson represented in the final playbook;
- 13 permanent card-reward skips with no same-reward reopen loop;
- a two-card-reward case skipped the first and processed the second correctly.

B2 is the final autonomous control used in analysis.

---

# 7. C2 authoritative-teaching redesign

The earlier C2 prototype allowed a second LLM to rewrite human feedback into revised strategic lessons.

This was removed because it weakened attribution: the treatment would otherwise be “human feedback + reviser interpretation” rather than direct human teaching.

Final design:

- Human strategy is stored verbatim.
- Metadata classification is allowed only for retrieval indexing.
- The acting LLM interprets the original human wording at decision time.
- Human strategic content is never silently rewritten.

---

# 8. C2 v1.2.0 invalidation

**Status: INVALIDATED**

Run 1 stored authoritative human teaching that explicitly discussed Neow and starting-relic strategy.

The teaching text was preserved correctly, but the metadata organizer omitted `GENERAL` from `applies_to`.

The controller maps:

```text
NEOW_BLESSING -> GENERAL
```

Therefore Run 2 did not retrieve the Run-1 authoritative rule at Neow.

The rule was retrieved later in another applicable context, isolating the problem to retrieval scope rather than storage or temporal memory.

Archive:

```text
spirecomm/runs/C2_v1_2_0_invalidated_metadata_scope_bug/
```

---

# 9. C2 v1.2.1 fix and mandatory scope smoke

v1.2.1 added two protections:

1. the metadata prompt explicitly describes controller decision-to-retrieval-category mappings; and
2. a deterministic safeguard adds `GENERAL` whenever authoritative human teaching explicitly mentions Neow or a starting-relic-to-boss-relic swap.

A dedicated scope smoke used isolated seeds:

```text
991301
991302
```

Pass condition:

- Run 1 finalized with `HUMAN_TEACHING` mentioning Neow/start-relic swap;
- Run 2 `NEOW_BLESSING` retrieval used `memory_category = GENERAL`;
- the Run-1 authoritative rule/source ID was present;
- `authoritative_rule_count >= 1`;
- `memory_count >= 1`;
- `playbook_updated_through_run = 1`.

**Result: PASS.**

The actor retrieved the Run-1 authoritative teaching at Run-2 Neow and selected the boss-relic swap consistent with that teaching.

v1.2.1 was then frozen for official collection.

---

# 10. Final C2 v1.2.1 treatment

**Status: COMPLETE / FROZEN**

Dataset:

```text
spirecomm/runs/C2_v1_2_1_15runs_final/
```

## Results

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

## Human-review distribution

- `HUMAN_TEACHING`: 10 runs
- `APPROVE_INITIAL`: 5 runs

## Integrity

- exactly 15 starts and 15 completions;
- 15 completed post-run reflections;
- exact official seed order;
- 3,705 memory retrieval events;
- zero detected current-run/future-run memory leakage;
- complete raw-memory source coverage;
- all authoritative human teaching preserved verbatim through actor-facing guidance.

## Runtime caveats

One transient API HTTP 500 occurred during Run 6 and recovered on attempt 2. No heuristic gameplay action was substituted.

Two LLM calls returned out-of-range indexes and used the frozen deterministic index-parser fallback:

- Run 3 event choice: raw answer `2` with two legal options; fallback selected index 0.
- Run 7 combat choice: raw answer `2` with Offering+ / End Turn; fallback selected End Turn.

These are retained as model-output/protocol failures. The runs were not selectively rerun after observing outcomes.

---

# 11. Final B2 vs C2 matched comparison

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

## Paired direction

Floor:

- C2 > B2 on 11/15 matched seeds;
- B2 > C2 on 4/15;
- mean paired gain: +8.60 floors for C2.

Score:

- C2 > B2 on 10/15 matched seeds;
- B2 > C2 on 5/15;
- mean paired gain: +106.87 points for C2.

## Interpretation

The strongest conclusion is:

> Under the matched cumulative-memory follow-up, authoritative human teaching improved survival depth and long-horizon progression relative to autonomous self-reflection.

The result should not be overstated. Neither system won. C2 therefore demonstrates materially better progression, not solved Slay the Spire gameplay.

See:

```text
spirecomm/docs/FINAL_B2_C2_ANALYSIS.md
```

for the consolidated analysis.

---

# 12. Archive/source-of-truth rules

Final analysis uses only:

```text
spirecomm/runs/B2_v1_1_1_15runs_final/
spirecomm/runs/C2_v1_2_1_15runs_final/
```

Do not mix in:

- smoke runs;
- interrupted attempts;
- B2 v1.1.0;
- C2 v1.2.0;
- development controller runs.

The structured event log is the machine-readable source of truth for run outcomes and runtime decisions.

The committed C2 final directory currently contains the official event log and controller snapshots. Raw C2 memory/playbook/reflection outputs were Git-ignored during collection; they were separately validated and should be preserved externally for full reflection-level reproducibility.

---

# 13. Next phase after the matched experiment

B2 has completed its role as the autonomous control.

C2 is the architecture selected for continuation.

The next research phase should separate learning from final evaluation:

## Extended C2 learning

- use fresh training seeds not used in the completed experiments/smokes;
- keep human review enabled;
- continue accumulating authoritative teaching and approved reflections.

## Freeze

At the end of the learning phase, freeze:

- controller code;
- raw memory;
- playbook;
- prompts/policies.

## Held-out evaluation

Use a separate unseen seed set with:

- learned memory retrieval enabled;
- human feedback disabled;
- post-run reflection updates disabled;
- memory/playbook writes disabled.

The held-out evaluation should answer whether human-taught knowledge generalizes to new runs rather than merely continuing to learn from the evaluation trajectories themselves.
