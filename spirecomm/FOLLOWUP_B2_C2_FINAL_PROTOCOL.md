# B2/C2 Final Follow-up Protocol

## Purpose

The B2/C2 follow-up tests whether **authoritative natural-language human teaching** improves an LLM game-playing agent beyond autonomous self-reflection.

- **B2 v1.1.1 — autonomous control:** completed trajectory -> LLM reflection -> cumulative memory/playbook.
- **C2 v1.2.0 — final human-taught system:** completed trajectory -> initial LLM reflection -> human review -> either approve those lessons unchanged or store the human's own teaching verbatim -> cumulative memory/playbook.

The actor model, character, Ascension level, gameplay controller, legal-action interface, base reflection schema, official seed order, and cumulative-memory infrastructure remain aligned. The intended treatment difference is the authoritative human teaching path in C2.

## What changed from B/C1

### Cumulative memory instead of newest-three retrieval

B/C1 retrieved at most the newest three matching lessons. B2/C2 permanently retain every final lesson in raw memory and consolidate the complete history into a cumulative playbook.

Every raw lesson ID must remain represented by at least one playbook rule.

### Trajectory-level human feedback

C1 asked the reviewer to accept/correct/reject/add structured lessons.

C2 instead presents the completed trajectory and initial reflection in a local browser UI. The reviewer writes one natural-language response describing what the LLM missed or misunderstood. The LLM then generates the final structured lessons from:

1. the trajectory;
2. the initial reflection;
3. the human feedback.

### Cross-category applicability — v1.1

C2 smoke v0.1 showed that a strategic idea can be learned in one context but matter in another. For example, an EVENT-derived lesson can contain CARD_REWARD deck-selectivity guidance.

`cumulative-playbook-v2` therefore stores:

- one primary `category`;
- an `applies_to` list containing every decision category where the rule is useful.

Retrieval scans the entire playbook and returns every applicable rule rather than only reading one category bucket.

### Authoritative human teaching — C2 v1.2.0

The original C2 smoke design used a second LLM to rewrite human feedback into revised lessons. The final C2 treatment removes that strategic rewriting layer.

After each completed run, the reviewer chooses:

- **APPROVE_INITIAL** — store the initial LLM reflection lessons unchanged; or
- **HUMAN_TEACHING** — store the reviewer's natural-language teaching verbatim.

For `HUMAN_TEACHING`, an LLM may infer only:

- a short neutral title;
- one primary category;
- an `applies_to` list.

The organizer may not paraphrase, summarize, correct, expand, or otherwise rewrite strategic content.

Authoritative human teaching is excluded from LLM playbook consolidation. Its actor-facing playbook rule is reconstructed deterministically from raw memory, and validation requires the playbook guidance to equal the stored human teaching.

## Matched seeds

### Smoke v0.2

Both B2 and C2 smoke controllers use:

`990001`, `990002`

### Official final matched set

Both official controllers use the same 15 seeds in the same order:

`260925001` ... `260925015`

Smoke seeds do not overlap the official set.

---

# Phase 1 — C2 smoke v0.2

**Status: COMPLETE.**

The two-run smoke validated cumulative-playbook-v2, complete raw-memory coverage, temporal isolation, and live cross-category retrieval. A separate stale-state edge case after Smoke Bomb was observed and patched in all current B2/C2 controllers before further collection.

## Clean only C2 smoke-v0.2 artifacts

From the project root:

```powershell
Remove-Item .\reflection\condition_c2_raw_memory_smoke_v02.jsonl -ErrorAction SilentlyContinue
Remove-Item .\reflection\condition_c2_playbook_smoke_v02.json -ErrorAction SilentlyContinue
Remove-Item .\reflection\condition_c2_feedback_smoke_v02.jsonl -ErrorAction SilentlyContinue
Remove-Item .\reflection\condition_c2_outputs_smoke_v02 -Recurse -Force -ErrorAction SilentlyContinue

Remove-Item .\spirecomm\run_events_c2_smoke_v02.jsonl -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\sts_messages_c2_smoke_v02.log -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\agent_debug_c2_smoke_v02.log -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\state_dumps_c2_smoke_v02.jsonl -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\EXPERIMENT_PAUSED_C2_SMOKE_V02.txt -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\SESSION_COMPLETE_C2_SMOKE_V02.txt -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\HUMAN_FEEDBACK_REQUIRED_C2_SMOKE_V02.txt -ErrorAction SilentlyContinue
```

The successful v0.1 smoke artifacts use different filenames and can remain untouched.

## Activate the C2 smoke controller

```powershell
Copy-Item .\spirecomm\test_connection_c2_smoke_v0_2.py .\spirecomm\test_connection.py -Force
```

## Start the feedback UI

In a second terminal from the project root:

```powershell
python .\reflection\feedback_app.py --output-dir .\reflection\condition_c2_outputs_smoke_v02
```

Open:

```text
http://127.0.0.1:8765
```

Keep the feedback UI running while Slay the Spire is running.

## Run Slay the Spire

Launch through ModTheSpire with CommunicationMod configured to run `spirecomm/test_connection.py`.

After each completed run:

1. the controller generates the initial reflection;
2. a pending feedback packet appears;
3. inspect the run summary, flagged candidates, strategic timeline, full trajectory as needed, and initial reflection;
4. write trajectory-level feedback;
5. click **Finalize feedback**;
6. the LLM generates the revised final reflection;
7. lessons are appended to raw memory;
8. the cumulative playbook is updated;
9. only then can the next run begin.

If the initial reflection is already adequate, use the **Initial reflection looks right** button. This records an explicit human judgement.

## C2 smoke-v0.2 success criteria

After two completed runs verify:

- `reflection/condition_c2_raw_memory_smoke_v02.jsonl` exists;
- `reflection/condition_c2_playbook_smoke_v02.json` exists;
- `reflection/condition_c2_feedback_smoke_v02.jsonl` exists;
- `reflection/condition_c2_outputs_smoke_v02/` contains both run packets/reflections;
- `spirecomm/run_events_c2_smoke_v02.jsonl` contains two valid `RUN_END` events;
- the playbook reports `playbook_version: cumulative-playbook-v2`;
- every raw memory ID appears in at least one playbook rule's `source_memory_ids`;
- cross-category rules contain appropriate `applies_to` values;
- Run 2 retrieval only uses knowledge available after Run 1;
- no current/future-run leakage occurs.

---

# Phase 2 — B2 smoke v0.2

**Status: COMPLETE.**

B2 completed two valid smoke runs with six raw lessons and seven final playbook rules. Temporal isolation, source coverage, live cross-category retrieval, and the Smoke Bomb transition guard were all verified.

## Clean only B2 smoke-v0.2 artifacts

```powershell
Remove-Item .\reflection\condition_b2_raw_memory_smoke_v02.jsonl -ErrorAction SilentlyContinue
Remove-Item .\reflection\condition_b2_playbook_smoke_v02.json -ErrorAction SilentlyContinue
Remove-Item .\reflection\condition_b2_feedback_smoke_v02.jsonl -ErrorAction SilentlyContinue
Remove-Item .\reflection\condition_b2_outputs_smoke_v02 -Recurse -Force -ErrorAction SilentlyContinue

Remove-Item .\spirecomm\run_events_b2_smoke_v02.jsonl -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\sts_messages_b2_smoke_v02.log -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\agent_debug_b2_smoke_v02.log -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\state_dumps_b2_smoke_v02.jsonl -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\EXPERIMENT_PAUSED_B2_SMOKE_V02.txt -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\SESSION_COMPLETE_B2_SMOKE_V02.txt -ErrorAction SilentlyContinue
```

## Activate B2 smoke

```powershell
Copy-Item .\spirecomm\test_connection_b2_smoke_v0_2.py .\spirecomm\test_connection.py -Force
```

Launch Slay the Spire and complete both smoke seeds.

## B2 smoke-v0.2 success criteria

Verify:

- two valid completed runs;
- a raw memory bank;
- cumulative-playbook-v2 output;
- complete source-memory coverage;
- cross-category `applies_to` values where appropriate;
- Run 2 retrieval of only Run-1 knowledge;
- no human-feedback dependency.

---

# Phase 3 — Official B2 v1.1.1 / C2 v1.2.0

## Final role of each condition

- **B2 is the control:** autonomous self-reflection with cumulative-playbook-v2.
- **C2 is the final proposed system:** the same gameplay architecture plus authoritative human review. Initial lessons are either approved unchanged or replaced by verbatim human teaching.
- The research question is whether the human-taught C2 system improves long-horizon decision-making relative to the autonomous B2 control.


Only begin after both smoke tests pass.

## Clean official artifacts before each condition

Official B2 and C2 must begin with empty condition-specific memory/playbook/output files. Do **not** copy smoke memory into the official experiment.

## B2 official

Activate:

```powershell
Copy-Item .\spirecomm\test_connection_b2_v1_1_1.py .\spirecomm\test_connection.py -Force
```

Main official files:

```text
reflection/condition_b2_raw_memory.jsonl
reflection/condition_b2_playbook.json
reflection/condition_b2_outputs/
spirecomm/run_events_b2.jsonl
```

The controller targets 15 valid completed runs and runs the full 15-run batch without planned session checkpoints.

## Official B2 completion status

**COMPLETE — final B2 v1.1.1 control frozen.**

Dataset: `spirecomm/runs/B2_v1_1_1_15runs_final/`

Aggregate control results:

- wins: 0/15
- mean floor: 18.73
- median floor: 16
- best floor: 29
- mean score: 144.60
- best score: 251
- Act 2: 6/15
- Act 3: 0/15
- final raw lessons: 38
- final playbook rules: 14

Integrity checks:

- exactly 15 starts and 15 valid completions;
- official requested seeds 260925001..260925015 in order;
- Run 1 empty memory;
- zero current/future memory leakage across 2,924 retrievals;
- complete raw-memory source coverage;
- card-reward skip guard validated in live official runs, including a two-card-reward case;
- no runtime/CommunicationMod/watchdog errors.

The older `B2_v1_1_0_invalidated_card_skip_bug` dataset is retained only for provenance and must not be used in the matched analysis.

---

## C2 official

Activate:

```powershell
Copy-Item .\spirecomm\test_connection_c2_v1_2_0.py .\spirecomm\test_connection.py -Force
```

Start the feedback UI:

```powershell
python .\reflection\feedback_app.py --output-dir .\reflection\condition_c2_outputs
```

Main official files:

```text
reflection/condition_c2_raw_memory.jsonl
reflection/condition_c2_playbook.json
reflection/condition_c2_feedback.jsonl
reflection/condition_c2_outputs/
spirecomm/run_events_c2.jsonl
```

C2 v1.2.0 targets 15 valid completed runs and runs the full 15-run batch without planned session checkpoints. It must begin with empty C2 memory, feedback bank, playbook, outputs, and event logs.

---

## Pre-official Smoke Bomb transition hotfix

C2 smoke v0.2 logged two invalid `PLAY` errors after Smoke Bomb ended an elite combat. CommunicationMod briefly returned a stale command-ready combat snapshot while transitioning out of combat.

All four B2/C2 smoke/official controllers now mark Smoke Bomb escape as pending and wait through up to five stale combat snapshots before normal routing resumes. The guard clears immediately when a non-combat foreground state appears.

This hotfix must remain identical in B2 and C2 official controllers.

---

## Smoke-validation gate

The pre-official gate is now satisfied:

- C2 smoke v0.2: PASS
- B2 smoke v0.2: PASS
- cumulative-playbook-v2 source coverage: PASS
- cross-category retrieval: PASS
- temporal isolation: PASS
- Smoke Bomb transition guard: PASS

B2 v1.1.1 is complete. Proceed to C2 v1.2.0 using the same 15 fixed seeds in the documented order.

---

## v1.1.1 card-reward skip correctness hotfix

CommunicationMod can continue exposing a skipped permanent card reward on the parent COMBAT_REWARD list. v1.1.0 therefore reopened skipped rewards.

v1.1.1 records skipped card-reward entries for the current reward flow and does not reopen them. If multiple card rewards exist, only the skipped entries are ignored and later distinct rewards remain available.

The final B2 control uses v1.1.1 and the final C2 treatment uses v1.2.0. Both contain the same card-reward skip guard. Do not carry memory from any discarded/interrupted run into C2 v1.2.0.

---

## C2 human-teaching protocol

For every completed C2 run, review the trajectory and initial reflection using the same five questions:

1. Did the initial reflection identify the real cause of failure?
2. Did it miss an important earlier strategic decision?
3. Is any claimed lesson factually or strategically wrong?
4. Is any proposed lesson too specific to the current run?
5. What generalizable rule should transfer to future runs?

Then choose exactly one review action:

### APPROVE_INITIAL

Use this only when the initial reflection already captures the teaching you want retained. Its original lessons are stored unchanged.

### HUMAN_TEACHING

Write the teaching naturally in your own words. The submitted text is authoritative and is stored as the strategic guidance itself. Do not write feedback merely describing how the reviser should change something; write what you actually want the future agent to remember.

The metadata organizer may tag the teaching for retrieval but may not rewrite its strategy.

Human review should not use future matched seeds or the B2 trajectory for the same seed. The reviewer may comment on any point visible in the completed C2 trajectory, including combat sequencing, card selection, route planning, keys, campfires, shops, potions, events, deck construction, and long-horizon strategic commitments.

---

# Experimental controls

- Do not change gameplay prompts, reflection rules, memory policy, seed order, or controller logic after official collection begins.
- Do not manually issue gameplay decisions to rescue a run.
- Infrastructure-interrupted attempts do not count as valid runs and must not generate learning memory.
- Every completed run must finish its post-run reflection/memory update before a later run starts.
- B2 and C2 must use the same 15 official seeds in the same order.
- Do not carry B2 memory into C2 or C2 memory into B2.
- Do not carry smoke memory into either official condition.
- In C2, review only the completed trajectory currently awaiting feedback. Do not inspect future runs when writing earlier feedback.

# Analysis plan

Report both aggregate and paired matched-seed comparisons.

Performance:

- floor;
- score;
- Act 2/Act 3 reach;
- wins.

Behaviour:

- card reward/skip decisions;
- campfire recovery decisions;
- shops/resource management;
- key acquisition and route planning;
- combat ordering/survival.

Learning:

- raw lesson count and category distribution;
- playbook rule count/category coverage;
- cross-category applicability;
- retrieval coverage over time;
- initial reflection vs APPROVE_INITIAL/HUMAN_TEACHING decisions;
- verbatim human-teaching themes and retrieval scopes;
- whether feedback corrects credit assignment and long-horizon failures.
