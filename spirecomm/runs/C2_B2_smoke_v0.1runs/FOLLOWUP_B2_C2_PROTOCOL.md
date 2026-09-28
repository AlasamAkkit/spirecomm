# B2/C2 Follow-up Experiment Protocol

## Purpose

This follow-up isolates the effect of trajectory-level human feedback while fixing the memory bottleneck discovered in B/C1.

- **B2 — Improved self-reflection:** completed trajectory -> LLM reflection -> cumulative memory/playbook.
- **C2 — Human-guided reflection:** completed trajectory -> LLM initial reflection -> human trajectory feedback -> LLM revised reflection -> the **same** cumulative memory/playbook.

The actor/controller, game state, model, reflection-v0.2, cumulative-memory mechanism, and matched game seeds are otherwise the same.

## What changed from B/C1

### 1. Human feedback is trajectory-level

C2 no longer asks the reviewer to ACCEPT/CORRECT/REJECT individual lesson fields. After each run, a local browser UI shows:

- run outcome and build summary;
- automatically flagged review candidates (these are **not** labelled mistakes);
- the strategic timeline;
- the full compact trajectory in an expandable section;
- the LLM's initial reflection.

The reviewer writes one natural-language response explaining what the LLM missed or misunderstood. The LLM then produces the final structured lessons using the trajectory + initial reflection + human feedback.

### 2. Memory is cumulative rather than newest-3

Every final lesson remains permanently in a raw JSONL memory bank.

The full bank is consolidated into a cumulative playbook. The playbook updater is validated so that **every raw lesson ID must remain represented by at least one playbook rule**. Older lessons therefore cannot silently disappear just because newer runs occur.

During gameplay the actor receives **all applicable playbook rules** for the decision category, plus GENERAL rules. There is no top-k=3 truncation.

### 3. B2 and C2 use matched seeds

Official B2 and C2 both use the same 15 seeds, in the same order:

`260925001` ... `260925015`

The smoke tests use `990001` and `990002` and do not overlap the official set.

## New files

Place these in the project:

```text
sts-llm-fyp/
├── reflection/
│   ├── followup_reflection.py
│   ├── feedback_app.py
│   ├── prepare_reflection.py          # existing
│   └── condition_c_reflection.py      # existing; supplies frozen v0.2 helpers
└── spirecomm/
    ├── test_connection_c2_smoke_v0_1.py
    ├── test_connection_b2_smoke_v0_1.py
    ├── test_connection_c2_v1_0_0.py
    └── test_connection_b2_v1_0_0.py
```

CommunicationMod should continue to launch `spirecomm/test_connection.py`, so copy the controller you want to test over that filename.

---

# Phase 1 — C2 browser/UI smoke test (2 runs)

## Clean only C2 smoke artifacts

From the project root:

```powershell
Remove-Item .\reflection\condition_c2_raw_memory_smoke.jsonl -ErrorAction SilentlyContinue
Remove-Item .\reflection\condition_c2_playbook_smoke.json -ErrorAction SilentlyContinue
Remove-Item .\reflection\condition_c2_feedback_smoke.jsonl -ErrorAction SilentlyContinue
Remove-Item .\reflection\condition_c2_outputs_smoke -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\run_events_c2_smoke.jsonl -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\sts_messages_c2_smoke.log -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\agent_debug_c2_smoke.log -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\state_dumps_c2_smoke.jsonl -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\EXPERIMENT_PAUSED_C2_SMOKE.txt -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\SESSION_COMPLETE_C2_SMOKE.txt -ErrorAction SilentlyContinue
Remove-Item .\spirecomm\HUMAN_FEEDBACK_REQUIRED_C2_SMOKE.txt -ErrorAction SilentlyContinue
```

## Activate C2 smoke controller

```powershell
Copy-Item .\spirecomm\test_connection_c2_smoke_v0_1.py .\spirecomm\test_connection.py -Force
```

## Start the browser feedback UI in a second terminal

```powershell
python .\reflection\feedback_app.py --output-dir .\reflection\condition_c2_outputs_smoke
```

Open:

```text
http://127.0.0.1:8765
```

Keep this terminal open.

## Launch Slay the Spire through ModTheSpire

After Run 1 completes:

1. the controller generates the initial reflection;
2. a pending review appears in the browser;
3. inspect the flagged events, strategic timeline, and full trajectory as needed;
4. write natural-language feedback;
5. click **Finalize feedback**;
6. the LLM revises its reflection, stores final lessons, updates the cumulative playbook, then starts Run 2.

### What to write as feedback

Focus on questions such as:

- What earlier decision actually contributed to the failure?
- Did the LLM blame the final combat when the cause occurred several floors earlier?
- Was there a long-horizon issue involving HP, routing, elites, keys, shops, or the boss?
- Did the agent already have enough damage/defence but continue solving the wrong problem?
- Was an important good decision worth reinforcing?

You do **not** need to edit JSON or write formal lessons.

If the initial reflection is already correct, use the **Initial reflection looks right** button. This records an explicit human judgement rather than leaving the feedback blank.

## Smoke-test success criteria

After 2 completed runs, verify:

```text
reflection/condition_c2_raw_memory_smoke.jsonl
reflection/condition_c2_playbook_smoke.json
reflection/condition_c2_feedback_smoke.jsonl
reflection/condition_c2_outputs_smoke/
spirecomm/run_events_c2_smoke.jsonl
```

Run 2 should retrieve playbook rules supported only by Run 1; there must be no current/future-run leakage.

---

# Phase 2 — B2 smoke test (2 runs)

B2 requires no browser feedback.

Clean B2 smoke artifacts, then:

```powershell
Copy-Item .\spirecomm\test_connection_b2_smoke_v0_1.py .\spirecomm\test_connection.py -Force
```

B2 should automatically reflect, append final lessons, update the same type of cumulative playbook, and continue.

Smoke files use the `b2_smoke` suffix and are separate from C2.

---

# Phase 3 — Official B2 and C2

The official controllers are configured for **15 valid completed runs each**, in 5-run sessions.

Do not carry smoke memories/playbooks into official runs.

## B2 official

```powershell
Copy-Item .\spirecomm\test_connection_b2_v1_0_0.py .\spirecomm\test_connection.py -Force
```

Official B2 files:

```text
reflection/condition_b2_raw_memory.jsonl
reflection/condition_b2_playbook.json
reflection/condition_b2_outputs/
spirecomm/run_events_b2.jsonl
```

## C2 official

```powershell
Copy-Item .\spirecomm\test_connection_c2_v1_0_0.py .\spirecomm\test_connection.py -Force
```

Run the browser UI:

```powershell
python .\reflection\feedback_app.py --output-dir .\reflection\condition_c2_outputs
```

Official C2 files:

```text
reflection/condition_c2_raw_memory.jsonl
reflection/condition_c2_playbook.json
reflection/condition_c2_feedback.jsonl
reflection/condition_c2_outputs/
spirecomm/run_events_c2.jsonl
```

## Important experimental controls

- Do not modify prompts, feedback rules, memory policy, or seed list after official runs begin.
- Do not manually make gameplay decisions if the controller/interface fails.
- Infrastructure-interrupted attempts do not count toward the valid-run target and must not contribute reflection/memory.
- B2 and C2 must keep the same 15 matched seeds and same controller logic.
- In C2, write feedback based on the completed trajectory. Do not inspect future runs or future memory while reviewing an earlier run.

## Analysis plan

Primary B2 vs C2 comparisons:

- mean/median floor and score;
- Act 2/Act 3 reach rates and wins;
- paired per-seed floor/score differences;
- card reward/skip behaviour;
- low-HP campfire decisions;
- key acquisition and route planning;
- playbook size/category coverage over time;
- human-feedback themes;
- initial reflection vs final human-guided reflection changes;
- whether human feedback specifically corrects credit assignment / long-horizon failures.

Because the seeds are matched, report both aggregate metrics and paired seed-by-seed differences.
