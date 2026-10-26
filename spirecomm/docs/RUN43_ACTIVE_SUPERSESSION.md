# Run-43 intervention: explicit human supersession and verifier guards

**Status:** Versioned code intervention, not a verified live Run-43 result.
Earlier runs remain attributed to their historical controllers. Requires
Run-42 finalized human feedback and playbook updated through Run 42.

## Why this intervention exists

- Run 1 human teaching (`c2_run_01_01`) advocated swapping Burning Blood
  for a random boss relic at Neow. Run 23 human teaching (`c2_run_23_01`)
  expressly reversed that advice.
- Both remain intact in the immutable raw human-memory bank and cumulative
  playbook; earlier controller versions presented both as authoritative.
- Runs 40–41 exposed verifier-replacement failures involving lethal damage,
  attack-intent uncertainty and action energy validity.

## Changes from A10 v1.4

1. Only at `NEOW_BLESSING`, active retrieval suppresses the superseded
   Run-1 **rule** while retaining the authoritative Run-23 rule. All
   historical raw lessons and the playbook on disk remain byte-for-byte
   unchanged. Other decision categories still retain the old rule's
   unrelated historical teaching.
2. When alternatives exist at Neow, exclude the starting-relic-for-random-boss-
   relic action. The original candidate list remains visible in the subsequent
   `ACTION` event; `RUN43_HUMAN_SUPERSESSION_APPLIED` records suppression.
   A game offering only a swap is not forced to emit an illegal alternative.
3. Before a verifier replacement is installed, reject demonstrably
   infeasible energy/hand sequences, replacements under unknown
   (`DEBUG`) enemy intents, and replacements that discard a provable
   lethal made solely of basic Strike/Thunderclap damage against one
   unprotected target. Rejections preserve the original actor plan and
   emit `RUN43_VERIFIER_REPLACEMENT_REJECTED`. All other verifier behavior
   remains inherited. The arithmetic is deliberately **not** a full
   game-state simulator.
4. Every new event records `controller_variant` as
   `c2-v1.5.0-run43-active-supersession-verifier-guards+a10`.
   Earlier controller source files and decision logs are not rewritten.

## Safely cut over on the user's laptop

1. **Stop the game and Python controller.** Keep the locally finalized
   Run-42 evidence and any uncommitted files intact.
2. Run `git status --short`. Preserve local uncommitted code separately
   if present; never `reset --hard` or `git clean` experiment data.
3. `git pull --ff-only origin master` after the working tree is safe.
4. Verify local Run-42 review FINALIZED and playbook
   `updated_through_run == 42`.
5. Run `python .\\spirecomm\\freeze_c2_run42_checkpoint.py` **before**
   starting the game. It creates a write-once ZIP under
   `spirecomm/runs/_local_checkpoints/`. This directory is gitignored.
   It does not launch a game or change working memory.
6. Run `python .\\spirecomm\\test_c2_run43_preflight.py` plus
   `python .\\spirecomm\\test_c2_stable_preflight.py`,
   `python .\\spirecomm\\test_c2_a10_policy.py`, and
   `python -m unittest discover -s .\\reflection\\tests -p "test_*.py" -v`.
7. Launch as before through `spirecomm/test_connection.py`. Verify
   `RUN_START` for run 43 records `active_ascension: 10` and the new
   controller variant. Check that Neow emits the supersession audit event
   when a boss swap is offered alongside alternatives.

**Do not replay Run 42's teaching or overwrite the raw/playbook files.**
The live snapshot is local, not included in the GitHub source commit.

## Research and attribution

Runs 39–42: A10 difficulty with frozen v1.4 gameplay, no explicit
supersession or verifier replacement gates.
Run 43+: A10 difficulty with the new v1.5 scope-limited policy and
verifier guards. Compare outcomes as separate controller phases.
Post-run review questions remain unverified candidate diagnoses, and
verifier events must be inspected before blaming actor decisions.

## Limitations

- This first migration encodes **one explicit historical correction**
  (Run 23 supersedes Run 1 at Neow), not a general-purpose NLP
  contradiction detector.
- Lethal detection is conservative and limited to a small known subset.
- The verifier still uses an LLM for plans not caught by guards.
- GitHub CI cannot verify local Run-42 data, CommunicationMod integration,
  or actual Run-43 gameplay.
