# Phase III — Extended C2 Teaching and Held-Out Evaluation

## Status

**DESIGN FROZEN — implementation has not started.**

Do not modify or run `test_connection.py` for Phase III until the final C2 v1.2.1 memory/playbook/feedback/output state has been preserved.

## Purpose

The completed B2/C2 matched experiment established that authoritative human teaching improved progression relative to autonomous self-reflection under the same cumulative-memory architecture.

Phase III asks the next two questions:

1. Can continued C2 teaching on fresh runs further develop the agent's cumulative strategy?
2. Does the final learned C2 playbook improve performance on completely unseen runs when learning is disabled?

Phase III is therefore split into a **learning phase** and a **held-out evaluation phase**. Evaluation seeds must never be used for teaching, debugging, smoke tests, or controller development.

---

# 1. Starting state

Phase III begins from the accepted C2 v1.2.1 state after the 15-run matched experiment:

- completed C2 runs: 15;
- raw lessons: 25;
- cumulative playbook rules: 17;
- playbook updated through Run 15;
- review decisions: 10 `HUMAN_TEACHING`, 5 `APPROVE_INITIAL`;
- 3,705 matched-experiment memory retrievals with zero current/future-run leakage.

This state is the initial training checkpoint for Phase III. It must be preserved separately before further learning.

The Phase III continuation must retain the original run numbering. New teaching runs are **C2 Runs 16–30**, so new raw-memory IDs continue as `c2_run_16_*` through `c2_run_30_*`. They must not restart from `c2_run_01_*`.

---

# 2. Seed policy

Seeds are randomly generated once, split into training and evaluation sets, and then frozen.

The game remains stochastic across runs because every run uses a different seed. Freezing the lists prevents accidental overlap and protects the held-out evaluation.

## Phase III training seeds — C2 Runs 16–30

These 15 seeds are for human-guided learning only:

1. `455058654`
2. `735018898`
3. `128344023`
4. `124516061`
5. `524979483`
6. `116326791`
7. `505589230`
8. `828076239`
9. `139975831`
10. `135842376`
11. `601320924`
12. `707802282`
13. `460707459`
14. `262984513`
15. `556137101`

## Held-out final evaluation seeds

These 15 seeds are reserved exclusively for the final frozen evaluation:

1. `534220962`
2. `559167807`
3. `708003507`
4. `614548965`
5. `102805721`
6. `176193979`
7. `290389358`
8. `131476974`
9. `548541412`
10. `476762858`
11. `750883690`
12. `338506507`
13. `782132934`
14. `107227511`
15. `139922577`

### Held-out rule

Until Phase III training is complete and the final C2 memory is frozen:

- do not launch these evaluation seeds;
- do not use them for smoke tests;
- do not inspect trajectories/outcomes for them;
- do not use them to choose or revise human teaching;
- do not make controller changes in response to their behavior.

Knowing the numeric seed identifiers is not itself considered gameplay leakage; using the generated games or outcomes during training is.

---

# 3. Phase III-A — extended C2 teaching

## Goal

Continue the already learned C2 agent for 15 additional fresh runs while preserving the v1.2.1 teaching policy.

## Run numbering

- prior matched experiment: Runs 1–15;
- Phase III training: Runs 16–30.

## Learning behavior

After every completed training run:

1. generate the initial LLM reflection;
2. review the completed trajectory in the browser UI;
3. choose exactly one of:
   - `APPROVE_INITIAL`; or
   - `HUMAN_TEACHING`;
4. for `HUMAN_TEACHING`, store the human text verbatim;
5. allow only metadata-only title/category/`applies_to` classification;
6. update persistent raw memory and cumulative playbook;
7. only then start the next run.

No strategic LLM rewriting of human teaching is reintroduced.

## Architecture freeze

Unless a correctness/infrastructure bug would invalidate the data, Phase III training keeps unchanged:

- actor model: `gpt-5.6-luna`;
- Ironclad;
- Ascension 0;
- legal-action interface;
- gameplay prompts;
- cumulative-playbook-v2;
- authoritative-human-teaching-v1;
- cross-category retrieval;
- card-reward skip guard;
- Smoke Bomb transition guard;
- shop-potion safety guard;
- reflection schema and review workflow.

Do not tune prompts or retrieval behavior based on Phase III outcomes. Any experiment-invalidating change requires a new version and explicit provenance.

---

# 4. Continuation-state isolation

The matched C2 v1.2.1 dataset must remain immutable.

Phase III should use separate working paths initialized from the frozen Run-15 state, for example:

```text
reflection/phase3_c2_raw_memory.jsonl
reflection/phase3_c2_playbook.json
reflection/phase3_c2_feedback.jsonl
reflection/phase3_c2_outputs/

spirecomm/run_events_c2_phase3_training.jsonl
spirecomm/sts_messages_c2_phase3_training.log
spirecomm/agent_debug_c2_phase3_training.log
spirecomm/state_dumps_c2_phase3_training.jsonl
```

The Phase III copies are allowed to grow. The original final C2 matched artifacts are not.

### Required lineage

The cleanest implementation is to initialize the Phase III event log and learning state from exact copies of the accepted C2 Run-15 files, then append Runs 16–30 under a new Phase III controller version while allowing the integrity validator to recognize the frozen v1.2.1 history.

This preserves:

- original `source_run_id` provenance;
- original memory IDs from Runs 1–15;
- `updated_through_run = 15` at Phase III start;
- new IDs beginning at Run 16;
- full temporal/source-coverage validation.

The continuation controller must not treat the imported 25 lessons as a fresh Run-1 memory bank.

---

# 5. Phase III training integrity checks

Before Run 16:

- imported raw memory contains exactly 25 lessons;
- imported playbook contains 17 rules;
- playbook reports `updated_through_run = 15`;
- every imported raw lesson ID is covered by the playbook;
- the Phase III event-history copy contains the accepted 15 prior C2 completions/reflections;
- next requested seed is the first Phase III training seed, `455058654`;
- next completed run number is 16.

After Run 30:

- total lineage contains 30 completed C2 runs;
- Phase III added exactly 15 valid completions;
- every Run 16–30 completion has a completed post-run review/reflection;
- zero current/future memory leakage;
- every raw memory ID remains covered by the playbook;
- human teaching remains verbatim;
- no held-out evaluation seed appears anywhere in training logs.

Then freeze the resulting state as the **final learned C2 agent**.

---

# 6. Phase III-B — final held-out evaluation

After Run 30, freeze:

- controller version;
- prompts;
- raw memory;
- playbook;
- retrieval logic;
- model/configuration.

During held-out evaluation there is **no learning**:

- no post-run reflection;
- no human feedback;
- no raw-memory writes;
- no playbook updates;
- no feedback-bank updates.

The frozen playbook may be retrieved normally during gameplay.

## Primary final comparison

Evaluate two agents on the same 15 held-out seeds:

### E0 — no-memory control

- same final gameplay controller and model;
- no learned playbook injected;
- learning disabled.

### E1 — final C2

- same final gameplay controller and model;
- frozen post-Run-30 C2 playbook available;
- learning disabled.

This comparison tests whether the learned strategy transfers to unseen runs rather than merely improving the trajectories on which it was taught.

### Optional secondary evaluation

If time/API budget permits, also evaluate the frozen **pre-extension C2 Run-15 checkpoint** on the same held-out seeds. This would separate:

- C2 after the original 15-run matched experiment; and
- C2 after 15 additional teaching runs.

It is secondary because it adds another 15 full gameplay runs.

---

# 7. Final evaluation metrics

Primary outcomes:

- wins;
- floor reached;
- score;
- Act 2+ reach rate;
- Act 3 reach rate.

Because E0 and E1 use matched held-out seeds, report both aggregate and paired results:

- mean/median floor;
- mean/median score;
- per-seed floor difference;
- per-seed score difference;
- number of seeds where E1 > E0, E1 < E0, or tie;
- boss/elite/hallway death distribution.

Secondary behavioral measures may include:

- card-reward skip rate;
- final deck size;
- low-HP campfire decisions;
- key acquisition;
- potion use;
- retrieval counts/categories for E1.

No post-hoc teaching is permitted on evaluation runs.

---

# 8. Interpretation boundaries

The completed B2/C2 experiment supports the claim that human teaching improved progression relative to autonomous self-reflection in the matched online-learning sequence.

Phase III held-out evaluation addresses a different question: whether the accumulated C2 knowledge transfers to fresh runs when the learning loop is frozen.

A positive held-out result supports **generalization of the learned external memory**. It does not imply model-weight learning, because the LLM weights are never updated.

If the final C2 agent does not outperform the no-memory control on held-out seeds, that is still an informative result: it would suggest that the online improvements were specific to the learning trajectory, insufficiently transferable, or too noisy at the chosen sample size.

---

# 9. Planned workload

Minimum planned additional gameplay:

- Phase III teaching: 15 C2 runs;
- final E0 no-memory evaluation: 15 runs;
- final E1 frozen-C2 evaluation: 15 runs.

Total minimum additional runs: **45**.

The optional pre-extension-C2 evaluation would increase this to 60.

---

# 10. Immediate next step

Before implementing the Phase III controller, preserve the complete accepted C2 Run-15 learning state—including the gitignored raw memory, playbook, feedback bank, and reflection outputs—inside the frozen C2 archive or another immutable local backup.

Only after that preservation step should `test_connection_c2_phase3_training_v1.py` be implemented and smoke-validated without using any reserved held-out seed.
