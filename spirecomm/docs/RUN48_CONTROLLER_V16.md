# Run 48+: v1.6 targeted controller repair

> **Current operational guide (2026-11-02).** Source and offline tests are committed; the local Run-47 archive and a live Run-48 game have **not** been verified by GitHub. See [A10 longitudinal ledger](RUNS_39_48_A10_EVALUATION.md) and [current status](CONTINUAL_C2_STATUS.md).

Starts after Run 47 at fixed Ascension 10. Historical v1.4 and v1.5 controllers, logs and raw human feedback remain unchanged.

## Confirmed defects addressed

- Run 46 Sentry fight: old sticky-plan matching compared only card and enemy name and selected the first match. v1.6 binds the original monster roster slot plus name, max HP and any available instance ID. A missing/changed/ambiguous target invalidates the continuation and triggers a fresh plan instead of silently targeting a different Sentry.
- Run 46 impossible three-Strike plan and Run 41 energy overspending: first-pass and verifier sequences reject repeated uses of the same initial hand-card instance, invalid targets, and provable energy deficits. A bad first-pass queue is dropped while its already-legal first action can still be evaluated. A bad verifier replacement is rejected.
- Runs 43 and 47 unknown-intent gating: the verifier prompt now labels unknown intent damage as unknown rather than zero. The old blanket rejection of all plans under DEBUG/UNKNOWN is replaced by a narrow check: reject a replacement that demonstrably loses known Block while unresolved live enemy intents remain. Otherwise allow evidence-grounded replacement proposals.
- New event label: c2-v1.6.0-run48-target-identity-plan-feasibility+a10. Audit events include RUN48_FIRST_PASS_PLAN_REJECTED, RUN48_STICKY_TARGET_REPLAN, RUN48_VERIFIER_REPLACEMENT_REJECTED and RUN48_VERIFIER_REPLACEMENT_ACCEPTED.

## Limitations and evaluation integrity

The new validator detects proven impossible plans. It is not a complete game simulator and will not determine every card, relic, status or potion effect. If the game silently replaces an identical same-slot monster without providing an instance identifier, identity cannot be guaranteed; changed roster and known identity fields are checked. LLM strategy may still be wrong. Synthetic offline tests cannot certify live gameplay or eliminate all future bugs. Preserve the two experimental phases: Runs 43–47 on v1.5, Run 48 onward on v1.6; no claim of a completed Run 48.

## Local cutover procedure

1. Stop STS and the Python controller. Ensure Run 47 review is FINALIZED and active playbook updated_through_run is at least 47.
2. Run git status --short and preserve all local modifications. Do not discard experiment data, raw memory or feedback. Then pull the updated master branch safely.
3. With STS still stopped, run python .\spirecomm\freeze_c2_run47_checkpoint.py. It creates a write-once, gitignored **local** archive at spirecomm/runs/_local_checkpoints/C2_through_run47_pre_v1_6.zip.
4. Run python .\spirecomm\test_c2_stable_preflight.py, python .\spirecomm\test_c2_a10_policy.py, python .\spirecomm\test_c2_run43_preflight.py, python .\spirecomm\test_c2_run48_preflight.py, and python -m unittest discover -s .\reflection\tests -p test_*.py -v.
5. Start STS as normal. Verify Run 48 starts at Ascension 10 with v1.6 controller_variant. Look at the new audit events in duplicate-enemy fights and flag any stale-target mismatches.

Do not launch before saving the local Run 47 boundary archive; GitHub does not contain the finalized local review ledger and cannot create that archive for you.
## C2 post-run reflection provenance (Run 48+)

The C2 follow-up reflection pipeline now appends a bounded, chronological
controller/verifier audit to the compact trajectory **only for v1.6 runs**.
It distinguishes original acting-agent plans, verifier replacements and
queued-target invalidations, with explicit uncertainty about counterfactual
outcomes. Earlier runs and the frozen shared reflection-v0.2 prompt remain
unchanged. Human review remains authoritative; an audit event alone does not
prove a mistake or an improvement. The wording of low-HP elite diagnostics
now identifies an HP reading as **during the encounter**, rather than
claiming it was the HP at entry without an entry-state observation.
