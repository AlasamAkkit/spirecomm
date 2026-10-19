# C2 continual teaching — stable controller (Run 37 onward)

## Status and research boundary

- Runs 1–36 retain their original controller version and human-feedback history.
- Run 36 used `c2-continual-teaching-v1.3.1-block-aware-verifier`.
- After Run 36 has a `POST_RUN_REFLECTION_COMPLETE` event and the playbook is updated through 36, take the *one-time* compressed research snapshot.
- Run 37 onward uses **the same code**: `spirecomm/test_connection_c2_stable.py` (v1.4.0).
- Future improvement comes from the feedback app's `HUMAN_TEACHING` / `APPROVE_INITIAL` reviews. Do not change controller versions to respond to ordinary losses.

### Why freeze the controller?

Without a fixed controller, observed improvement mixes the effects of human teaching and changing executor code. The stable controller holds the system constant and preserves complete cumulative rule coverage. It intentionally does not promise optimal play or perfect knowledge of all game mechanics.

### What the stable controller fixes

- v1.3: no top-k forgetting; all applicable learned rules and state-matched old authoritative teaching included.
- v1.3.1: effective Block arithmetic recognizes Frail and Dexterity for a supported set of printed-Block cards.
- v1.4: sticky combat plans are invalidated at room/encounter transitions, queued `End turn` actions are reverified against the live state, and a known imminent attack triggers a defensive override rather than unnecessary passing **when a legal simple Block card can reduce HP loss**.
- Overridden decisions are recorded as `STABLE_END_TURN_GUARD`, `STABLE_STICKY_PLAN_INVALIDATED` or `STABLE_QUEUED_END_TURN_DROPPED`.

This is intentionally a small execution-hardening layer. It is **not** a full card-effect simulator. Novel enemy effects, alternative win conditions, hidden damage modifiers, potion value and deck strategy still require model reasoning and accumulated teaching.

## One-time activation (after Run 36 is finalized)

Close game/controller before changing code.

In PowerShell from project root:

```powershell
git pull origin master

# Check Run 36 is reflected before activating stable mode.
@'
import json
from pathlib import Path
p = Path("reflection/condition_c2_playbook.json")
print("playbook updated through:", json.loads(p.read_text(encoding="utf-8")).get("updated_through_run"))
'@ | python -

python .\spirecomm\freeze_c2_run36_stable_baseline.py
python -m py_compile .\spirecomm\test_connection_c2_stable.py
python .\spirecomm\test_c2_stable_preflight.py
```

Preflight should report `OK` for every unit test, with no errors or failures. If any test fails, **do not activate stable gameplay**.

Optional research provenance commit:

```powershell
git add .\spirecomm\runs\C2_continual_through_run36_pre_stable
git commit -m "chore: freeze C2 continual stable baseline through run 36"
git push origin master
```

Only after successful checkpoint and test:

```powershell
Copy-Item .\spirecomm\test_connection_c2_stable.py .\spirecomm\test_connection.py -Force
python -m py_compile .\spirecomm\test_connection.py
```

**This copy is done only once.** No more per-run controller swaps.

## Ordinary teaching loop (repeat without code changes)

1. Start the feedback UI in a separate terminal (keep it open):
   ```powershell
   python .\reflection\feedback_app.py --output-dir reflection/condition_c2_outputs
   ```
   Open <http://127.0.0.1:8765>.
2. Launch Slay the Spire with the existing mods/controller setup. If the controller is started manually in your existing working arrangement, use `python .\spirecomm\test_connection.py`; **do not launch a second controller process** if the mod already launched one.
3. One run finishes. The controller generates a trajectory and initial reflection and **waits for human review**. Select `HUMAN_TEACHING` to add/correct behavior or `APPROVE_INITIAL` if the reflection already captures the right lessons.
4. Finalize review in the feedback app. The controller appends authoritative feedback, updates the cumulative playbook and logs `POST_RUN_REFLECTION_COMPLETE`; only then may the next run start.
5. Repeat steps 3–4. **Do not edit/copy/reinstall the agent between runs.**

If you want to end a session, stop the controller **between completed runs**; keep the JSONL and reflection files intact. On restart it resumes from the event log and recovers pending feedback/reflection as designed.

## Checking progress

```powershell
@'
import json
from pathlib import Path
p = Path("spirecomm/run_events_c2.jsonl")
last = {}
counts = {}
for line in p.open(encoding="utf-8"):
    if not line.strip():
        continue
    e = json.loads(line)
    t = e.get("event_type")
    counts[t] = counts.get(t, 0) + 1
    if t in ("RUN_START", "RUN_END", "POST_RUN_REFLECTION_COMPLETE", "STABLE_END_TURN_GUARD"):
        last[t] = e
for k in ("RUN_START", "RUN_END", "POST_RUN_REFLECTION_COMPLETE"):
    x = last.get(k) or {}
    print(k, "run", x.get("completed_run_number"), "controller", x.get("continual_controller_version"))
print("safe end-turn overrides:", counts.get("STABLE_END_TURN_GUARD", 0))
p = Path("reflection/condition_c2_playbook.json")
print("playbook through:", json.loads(p.read_text(encoding="utf-8")).get("updated_through_run"))
'@ | python -
```

Expected stable provenance: `c2-continual-teaching-v1.4.0-stable-feedback-loop`. Historical `agent_version` and `experiment_tag` still use the frozen C2 lineage for validation; `continual_controller_version` is the version field for this phase.

## Feedback format

Give short specific teaching with a concrete state, desired behavior and an exception. Example:

> At 25/80 HP with known incoming damage, check effective Block before ending the turn. Use a legal defensive card when it meaningfully reduces HP loss, unless a guaranteed kill or other demonstrated higher-value play makes that unnecessary.

Avoid teaching rigid card bans or unconditional targeting rules based on one run. Separate defects in command routing from agent strategic mistakes.

## When to change code

Freeze the controller for the planned longitudinal evaluation window (for example Runs 37–50). Continue reviewing results, but do not patch it because one run loses. Modify code only for a **reproducible software defect** such as an invalid command, skipped/duplicated review, corrupted log, missing rule, or plan crossing encounters. If a defect forces a hotfix, save a checkpoint and document the exact new intervention boundary.

Evaluate across a window of multiple runs; outcomes across different random seeds cannot be directly attributed to a particular lesson.
