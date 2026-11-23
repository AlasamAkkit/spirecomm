# Run 56+ / v1.7.1 controller — post-Run-55 correction

This is a **new intervention boundary**, not a rewrite of Run 55.
The user confirmed a write-once Run-55 checkpoint after finalizing
HUMAN_TEACHING (30 files, SHA-256 manifest). That checkpoint, raw memory,
full run ledger and private teaching remain **local**; do not commit them.
Historical `test_connection_c2_run55.py` and `run55_policy.py` remain unchanged.

## Run 55 evidence and interpretation

- Ironclad, A10, Act 1 Floor 7, death to Lagavulin, score 62.
- Memory selection was active, but card-reward prompts sometimes prioritized
  COMBAT/GENERAL lessons over CARD_REWARD lessons.
- On Lagavulin turn 8, at 10 HP facing 20 attack damage and enemy at 22 HP,
  the verifier approved Bash+ then Strike as a 24-damage lethal using printed
  attack damage and Vulnerable. The attacks did not kill Lagavulin, which
  survived with 9 HP after debuff-reduced damage.
- The initial reflection's complaint about unused Defends on turn 7 was
  misleading: the enemy had STRONG_DEBUFF intent, not ATTACK. The user
  finalized corrective HUMAN_TEACHING, preserved only on the local machine.
- The run carried 319 unspent gold and spent 12 HP on repeated relic-event
  attempts. These are review findings, not evidence of a controlled win-rate
  regression. Do not publish private human teaching to GitHub.

## v1.7.1 implementation

1. Keep v1.7.0 retrieval, checkpoint and controller source as historical.
2. Preserve every state-matched authoritative human pin while reserving up to
   two rule slots for the decision's primary category (e.g. CARD_REWARD).
   When too many rules are pinned, the eight-rule limit remains SOFT and the
   controller may exceed it. The original playbook is never pruned.
3. Add a deliberately narrow negative-Strength nonlethal screen for known
   ordinary Strike/Bash/Thunderclap sequences. An optimistic 2x damage
   multiplier cannot rescue every plan. This screen can refute some false
   lethal claims but CANNOT certify lethal and is not a full simulator.
4. Send live Strength and the nonlethal certificate into the existing combat
   verifier prompt. Distinguish enemy ATTACK from pure STRONG_DEBUFF.
5. Audit zero-loss verifier approvals contradicting the screen under known
   incoming attack as RUN56_UNFOUNDED_LETHAL_FLAGGED. Only automatically
   substitute a legal Defend if its known projected Block turns otherwise
   lethal incoming damage into survival; otherwise retain the legal action
   without endorsing the erroneous lethal estimate.
6. Require matching finalized Run-55 review, reflection ledger, playbook
   updated through Run 55 and the immutable write-once Run-55 checkpoint.

**Limitations:** The controller does not solve all combat damage mechanics,
all resource-use strategy, or every possible unsupported LLM claim. Run 56
is the first live evaluation of this correction; no live performance benefit
or win-rate improvement is claimed.

## Local activation (Windows, from FYP project root)

Stop Slay the Spire and the controller. Verify your saved checkpoint still
exists at:

    spirecomm/runs/_local_checkpoints/C2_through_run55_post_v1_7.zip

The user already created and verified this checkpoint. Do not rerun the
freezer. Do not delete or regenerate the archive.

After merging, inspect any local uncommitted files before switching branches:

```powershell
git status --short
git fetch origin
git switch master
git pull --ff-only origin master
& .\spirecomm\venv\Scripts\python.exe .\spirecomm\test_c2_run55_preflight.py
& .\spirecomm\venv\Scripts\python.exe .\spirecomm\test_c2_run56_preflight.py
```

CommunicationMod still launches `spirecomm/test_connection.py`, now
binding the Run-56 agent. Start only one controller. Expect
`RUN56_V171_READY`, `next_run=56`, and variant
`c2-v1.7.1-run56-damage-sanity-decision-memory+a10`.
Keep final feedback for each run and compare variants only with explicit,
reproducible experimental design.

Historical Run-55 files, memory, feedback and checkpoints must not be
modified or included in a public Git commit.
