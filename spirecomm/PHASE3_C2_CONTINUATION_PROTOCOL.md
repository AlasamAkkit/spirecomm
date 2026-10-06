# Phase III — Open-Ended Continual C2 Teaching

## Status

**ACTIVE DESIGN — controller implemented as `c2-continual-teaching-v1.0`.**

The fixed B2/C2 matched experiment is complete. Phase III is no longer a second fixed 15-run comparison. Instead, the accepted C2 agent is now treated as one continuously taught agent whose progress is followed over fresh runs and increasing Ascension levels.

---

# 1. Research purpose

The completed B2/C2 experiment answered the controlled question:

> Does authoritative human teaching improve the agent relative to autonomous self-reflection under the same cumulative-memory architecture?

C2 performed substantially better on progression and score, so C2 is carried forward.

Phase III asks a different, open-ended question:

> How far can the same C2 agent progress when a human continues teaching it after every run?

The primary long-horizon milestone becomes **game completion and Ascension progression**, rather than another fixed-size B2/C2 comparison.

---

# 2. Starting checkpoint

Phase III begins from the accepted C2 v1.2.1 state after the matched 15-run experiment:

- completed C2 runs: 15;
- raw lessons: 25;
- cumulative playbook rules: 17;
- playbook updated through Run 15;
- review decisions: 10 `HUMAN_TEACHING`, 5 `APPROVE_INITIAL`;
- 3,705 memory retrievals with zero current/future-run leakage;
- Ascension: 0;
- wins: 0.

The frozen matched checkpoint remains preserved under:

```text
spirecomm/runs/C2_v1_2_1_15runs_final/
```

The active continual agent keeps the same memory lineage. New runs therefore begin at **Run 16**, and new memory IDs continue as `c2_run_16_*`, `c2_run_17_*`, and so on.

---

# 3. Continual teaching loop

For every new run:

```text
fresh random seed
      ↓
C2 plays the run
      ↓
initial LLM reflection
      ↓
human reviews trajectory
      ↓
APPROVE_INITIAL
or
HUMAN_TEACHING
      ↓
raw memory + cumulative playbook update
      ↓
next fresh random run
```

The C2 v1.2.1 teaching policy remains unchanged:

- `APPROVE_INITIAL` stores the initial LLM lessons unchanged;
- `HUMAN_TEACHING` stores the human's strategic text verbatim;
- the metadata-only organizer may assign title/category/`applies_to` only;
- authoritative human teaching is not strategically rewritten;
- authoritative rules are reconstructed deterministically from raw memory.

---

# 4. Seed policy

Runs after the Run-15 checkpoint use a **new random seed for every run**.

The controller generates a fresh nine-digit seed from the operating-system random source and immediately persists the assignment in:

```text
spirecomm/c2_continual_seed_schedule.json
```

This gives two properties:

1. every new gameplay run is fresh rather than replaying the original matched seeds;
2. if the program restarts after a seed has been assigned, that run keeps the same stored seed instead of silently changing.

The original matched seeds `260925001` through `260925015` remain associated only with Runs 1–15.

The continual seed generator rejects repeats against both the original 15 seeds and all previously generated continual seeds.

---

# 5. Ascension progression policy

The continual agent begins Phase III at **Ascension 0**.

It remains at the current Ascension until it wins a run. After a win and completion of that run's human review/reflection:

```text
A0 win -> next run A1
A1 win -> next run A2
A2 win -> next run A3
...
A19 win -> next run A20
```

At A20, further runs remain at A20.

The same cumulative memory is retained across Ascension levels. Memory is **not reset** after a clear; the purpose is to follow one continuously taught agent through an increasingly difficult curriculum.

Ascension progression is reconstructed from the structured event log on every startup, so a crash cannot silently lose a recorded clear. A derived convenience state is also written to:

```text
spirecomm/c2_continual_progress.json
```

The event log remains the source of truth.

---

# 6. Architecture freeze

Phase III changes run management, not the learned-policy architecture.

The following remain inherited unchanged from the frozen C2 v1.2.1 controller:

- actor model: `gpt-5.6-luna`;
- character: Ironclad;
- legal-action generation;
- gameplay prompts;
- cumulative-playbook-v2;
- all-applicable cross-category retrieval;
- authoritative-human-teaching-v1;
- reflection schema;
- browser feedback workflow;
- card-reward skip guard;
- Smoke Bomb transition guard;
- shop-potion safety guard;
- API retry/pause policy;
- raw-memory/playbook coverage validation;
- completed-run reflection recovery.

The continual wrapper dynamically loads the frozen controller:

```text
spirecomm/runs/C2_v1_2_1_15runs_final/test_connection_c2_v1_2_1.py
```

The active files are:

```text
spirecomm/test_connection.py
spirecomm/test_connection_c2_continual_v1.py
spirecomm/prepare_c2_continual.py
```

`test_connection.py` and `test_connection_c2_continual_v1.py` are intended to be byte-identical.

---

# 7. Checkpoint preservation and bootstrap

Before the first continual Run 16, run:

```powershell
python .\spirecomm\prepare_c2_continual.py
```

The bootstrap refuses to proceed unless it sees the accepted Run-15 checkpoint:

- completed runs exactly 1–15;
- 25 raw lessons;
- 17 playbook rules;
- `updated_through_run = 15`;
- unique memory IDs;
- complete raw-memory source coverage.

It then copies the active final C2 learning state into the frozen C2 archive, including the gitignored raw memory, playbook, feedback bank, and reflection outputs when present.

This step must be performed **once**, before Run 16.

---

# 8. Data continuity

The continual phase intentionally continues the same active C2 lineage:

```text
reflection/condition_c2_raw_memory.jsonl
reflection/condition_c2_playbook.json
reflection/condition_c2_feedback.jsonl
reflection/condition_c2_outputs/
spirecomm/run_events_c2.jsonl
```

The frozen Run-15 archive is the immutable checkpoint. The active files are allowed to grow from Run 16 onward.

New events retain the original C2 v1.2.1 agent/experiment identity so the existing integrity validator can verify the complete lineage, but they additionally contain:

- `research_phase = continual_teaching`;
- `continual_controller_version = c2-continual-teaching-v1.0`;
- `active_ascension`;
- `checkpoint_completed_runs = 15`.

This distinguishes the longitudinal phase from the original matched experiment without breaking source-run validation.

---

# 9. Primary Phase III measurements

Unlike the matched B2/C2 experiment, Phase III has no fixed planned number of runs.

The main outcomes are longitudinal milestones:

- run number of first A0 win;
- number of attempts required to clear each Ascension;
- highest Ascension reached;
- highest Ascension cleared;
- total wins;
- floor and score trajectory over time;
- memory and playbook growth;
- human-teaching vs `APPROVE_INITIAL` frequency;
- qualitative strategic changes associated with successful clears.

A useful summary table is:

| Ascension | Attempts | Wins | Run of first clear | Best floor/score |
|---:|---:|---:|---:|---:|
| 0 | ... | ... | ... | ... |
| 1 | ... | ... | ... | ... |
| 2 | ... | ... | ... | ... |

The project may stop when one of the following occurs:

- A20 is cleared;
- the FYP time/API budget is reached;
- performance reaches a stable plateau worth analysing.

---

# 10. Interpretation boundary

The original B2/C2 15-run matched experiment remains the controlled evidence for the effect of human teaching.

Phase III is a **longitudinal continual-teaching study**, not a new randomized comparison. Its purpose is to characterize how far the selected C2 architecture can be pushed through repeated human instruction.

Therefore claims from Phase III should focus on:

- achieved capability;
- learning trajectory;
- Ascension progression;
- recurring lessons and corrections;
- limits or plateaus.

It should not replace the matched B2/C2 experiment as the causal comparison between human teaching and autonomous reflection.

---

# 11. Operational start procedure

After pulling the latest repository changes:

```powershell
git pull origin master
python .\spirecomm\prepare_c2_continual.py
```

Then confirm the active and versioned continual controllers are identical:

```powershell
(Get-FileHash .\spirecomm\test_connection.py).Hash -eq `
(Get-FileHash .\spirecomm\test_connection_c2_continual_v1.py).Hash
```

Expected:

```text
True
```

Start the feedback UI:

```powershell
python .\reflection\feedback_app.py --output-dir .\reflection\condition_c2_outputs
```

Then launch Slay the Spire with CommunicationMod.

The first continual run should be:

```text
completed run number before start = 15
next run = 16
Ascension = 0
raw memory = 25 lessons
playbook = 17 rules
seed = newly generated random seed
```

After every run, complete the normal C2 feedback review before the next run begins.
