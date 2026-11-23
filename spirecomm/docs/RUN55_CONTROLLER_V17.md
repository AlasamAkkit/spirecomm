# Run 55+ — C2 controller v1.7.0 candidate (memory relevance + JSON safety)

**Status:** isolated development branch. Historical runs 1–54 and v1.6.1
remain unchanged. GitHub does **not** include the local Run-54 final feedback,
playbook, 95 MB event ledger or write-once checkpoint. The user must verify
them on the playing machine before activation.

## What changed

- `test_connection_c2_run55.py` inherits the **entire** Run-49 v1.6.1
  controller. Existing enemy targeting, equivalence matching, feasibility
  checks, block projections, and X-cost guards remain inherited.
- `run55_policy.py` transparently selects a smaller, relevant set of
  applicable playbook rules (soft target 8). Entity-matched authoritative
  teaching is pinned even when this exceeds 8. All original human
  teaching remains verbatim in the local raw-memory and playbook files.
- The original cumulative playbook remains fully checked for coverage.
  Only prompt selection changes. New `MEMORY_RETRIEVAL` records document
  selected/omitted rule IDs and the final prompt length. The old full-candidate
  audit is recorded separately as `RUN55_MEMORY_CANDIDATES`.
- Local, safe JSON trailing-comma normalization repairs the exact structural
  failure seen in Run 54's boss card reward (LLM scores favored Offering, but
  a terminal trailing comma caused the old controller to pick Skip).
- If a card-reward response is still invalid, the controller logs
  `RUN55_CARD_REWARD_PARSE_PAUSED` and pauses **without issuing a reward
  command**. It does not quietly choose Skip on invalid JSON.
- The planner/verifier receive an explicit conditional-human-teaching reminder
  and uncertainty warning. No verifier calls are removed in v1.7.

This is an experimental intervention, not proof of improved win rate or
guaranteed lower latency. Do not compare different-seed run outcomes as a
controlled controller ablation.

## Activation: exact steps (Windows PowerShell)

**Before starting: completely close Slay the Spire, ModTheSpire and the
Python controller.** Ensure the Run-54 feedback review says `FINALIZED`,
the playbook has `updated_through_run=54`, and the ledger contains the
matching `POST_RUN_REFLECTION_COMPLETE`. The v1.7 checkpoint freezer checks
all three automatically and refuses an incomplete boundary.

From the project root:

```powershell
git status --short
git fetch origin fyp/v1.7-run55-memory-efficiency
git switch --track origin/fyp/v1.7-run55-memory-efficiency

& .\spirecomm\venv\Scripts\python.exe .\spirecomm\test_c2_run55_preflight.py
& .\spirecomm\venv\Scripts\python.exe .\spirecomm\freeze_c2_run54_checkpoint.py
```

If a branch with the same local name already exists, use
`git switch fyp/v1.7-run55-memory-efficiency` instead of `--track`.
If `git status --short` shows modified tracked files, do **not**
force-switch or reset them. Check your changes first.

The freeze command writes the **local-only, write-once** archive:

```text
spirecomm/runs/_local_checkpoints/C2_through_run54_pre_v1_7.zip
```

This ZIP must stay on the local machine; it is intentionally gitignored.
Never delete or recreate earlier Run-42, 47 or 48 checkpoints.

Optionally validate the actual launcher while STS is closed:

```powershell
& .\spirecomm\venv\Scripts\python.exe .\spirecomm\test_connection.py
```

Expect `ready` and a `RUN55_V17_READY` entry in the local debug log.
Press Ctrl+C to stop the manual controller **before** launching ModTheSpire.

The CommunicationMod config still points to `spirecomm/test_connection.py`.
You do not need to change the configured command. Launch the game with
BaseMod + CommunicationMod; the next run must be Run 55 at Ascension 10.

**Never manually issue `START` or run a second Python controller while the
mod owns the subprocess.**

## Tests / interpretation

Run the earlier offline preflights as well (in separate processes):

```powershell
& .\spirecomm\venv\Scripts\python.exe .\spirecomm\test_c2_run49_preflight.py
& .\spirecomm\venv\Scripts\python.exe .\spirecomm\test_c2_run55_preflight.py
```

No LLM requests are made by either script.

Monitor Run 55's `RUN_START`, `controller_variant`,
`MEMORY_RETRIEVAL` selected/omitted counts, `LLM_CALL` input tokens
and latency, `COMBAT_PLAN_VERIFICATION_V13` latency, invalid plans,
and `RUN55_CARD_REWARD_PARSE_PAUSED` if any. Report results by
the exact controller variant from the event, not by current file names.

For any pause, preserve local logs, review, memory and playbook; do not
clear the event ledger or delete checkpoints. The earlier v1.6.1
`test_connection_c2_run49.py` remains available on this branch and on
`master` as the historical baseline. A return to the old launcher
after Run 55 has started would be a **new version transition** and must
be recorded, not silently mixed.

## Known limitations / further evaluation

This release keeps both LLM planner and verifier calls for new combat
plans. It reduces memory text exposed to those calls, but does **not**
halve the number of calls; real-world speed must be measured, not assumed.
Rule ranking is a simple deterministic heuristic with a soft limit, not a
complete semantic relevance model. New human teaching can still disagree
with old teaching; observe mismatch and correct by explicit future
feedback rather than rewriting the archival playbook.
