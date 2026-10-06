# FYP Changelog

This changelog records research/controller changes for the Slay the Spire LLM FYP. The package-level historical `spirecomm/CHANGELOG.md` is separate.

## C2 v1.2.1 — final authoritative human-taught dataset complete

### Result

- Completed all 15 matched C2 runs using seeds `260925001` through `260925015` in order.
- 0 wins.
- Mean floor 27.33; median 23; best 50.
- Mean score 251.47; median 197; best 629.
- Act 2+: 13/15.
- Act 3: 2/15.
- Final memory: 25 raw lessons.
- Final playbook: 17 rules.
- Human review: 10 `HUMAN_TEACHING`, 5 `APPROVE_INITIAL`.
- Zero current/future memory leakage across 3,705 retrievals.
- All authoritative teaching preserved verbatim in actor-facing guidance.

### Runtime notes

- One transient API HTTP 500 recovered on attempt 2; no gameplay fallback substituted.
- Two LLM calls returned out-of-range action indexes and used the existing deterministic index-parser fallback.
- These runs were retained rather than selectively rerun.

### Matched comparison

Compared with final B2 v1.1.1:

- C2 mean floor: 27.33 vs B2 18.73.
- C2 mean score: 251.47 vs B2 144.60.
- C2 Act 2+: 13/15 vs 6/15.
- C2 Act 3: 2/15 vs 0/15.
- C2 higher floor on 11/15 matched seeds.
- C2 higher score on 10/15 matched seeds.

C2 is selected as the architecture to carry forward.

---

## C2 v1.2.1 — retrieval-scope fix

### Bug in v1.2.0

The first authoritative-teaching attempt stored Run-1 Neow guidance verbatim, but the metadata organizer omitted `GENERAL` from `applies_to`. Because `NEOW_BLESSING` routes through the `GENERAL` retrieval category, Run 2 did not retrieve the teaching at Neow.

### Fix

- Added explicit controller-decision -> retrieval-category mapping to the metadata prompt.
- Added deterministic `GENERAL` scope enforcement when teaching explicitly mentions Neow or a starting-relic-to-boss-relic swap.
- Corrected the Neow detection regex.
- Added dedicated scope-smoke controller with isolated seeds.

### Validation

The v1.2.1 scope smoke verified that Run-1 authoritative Neow teaching appeared in Run-2 `NEOW_BLESSING` retrieval and influenced the actor decision.

The v1.2.0 attempt was archived as invalidated provenance.

---

## C2 v1.2.0 — authoritative human teaching redesign

### Changed

- Removed the second strategic LLM reviser from the active C2 pipeline.
- Added explicit review modes:
  - `APPROVE_INITIAL`: store initial reflection lessons unchanged.
  - `HUMAN_TEACHING`: store human natural-language teaching verbatim.
- Added metadata-only organizer limited to title, category, and `applies_to`.
- Added `authoritative-human-teaching-v1` policy metadata.
- Authoritative playbook rules are excluded from LLM strategic consolidation and regenerated deterministically from raw memory.
- Added validation requiring authoritative actor-facing guidance to equal stored human teaching.
- Actor prompts label authoritative rules clearly.

### Motivation

Allowing a second LLM to rewrite human feedback made the treatment depend on both human teaching and reviser interpretation. The redesign makes the human text the strategy source of truth.

---

## Final B2 v1.1.1 control complete

- Re-ran all 15 matched B2 seeds from empty memory after the card-reward fix.
- 15 starts, 15 completions, 15 reflections.
- 0 wins.
- Mean floor 18.73; median 16; best 29.
- Mean score 144.60; best 251.
- Act 2+: 6/15; Act 3: 0/15.
- 38 raw lessons; 14 final playbook rules.
- Complete source-memory coverage.
- Zero current/future leakage across 2,924 retrievals.
- 13 permanent card-reward skips completed without reopening the same declined reward.
- One multi-card-reward case skipped the first and correctly advanced to the second.
- Archived under `spirecomm/runs/B2_v1_1_1_15runs_final/`.

---

## v1.1.1 — permanent card reward skip guard

### Bug

CommunicationMod could continue exposing a skipped permanent card reward on the parent `COMBAT_REWARD` list. The old controller reopened the visible reward, overriding the earlier Skip intent.

### Measured impact in invalid B2 v1.1.0

- 92 skip actions;
- 19 affected reward instances;
- 9/15 affected runs;
- worst instance: 29 repeated skips;
- all affected instances eventually took a card or Singing Bowl.

### Fix

- Added per-reward-flow skipped-card tracking.
- Never reopen an entry that was deliberately skipped.
- Preserve later distinct card rewards such as Prayer Wheel.
- Applied identically to B2 and C2.

The old B2 batch was invalidated and B2 restarted from empty memory.

---

## B2 v1.1.0 — invalidated cumulative-memory batch

The batch completed structurally and demonstrated cumulative-memory behavior, but it is not used as a final result because the card-reward loop changed gameplay and downstream learning.

Historical diagnostic performance:

- 0 wins;
- mean floor 28.07;
- median 27;
- best 50;
- Act 2: 11/15;
- Act 3: 4/15;
- 41 raw lessons;
- 16 playbook rules.

Retained only for provenance.

---

## B2/C2 v1.1 — cumulative-playbook-v2

### Added

- `applies_to` scopes on playbook rules.
- Full-playbook retrieval of all rules applicable to the current decision category.
- Separation of primary provenance category from decision applicability.
- Validation of source-memory coverage.
- Matched official seed list `260925001`...`260925015`.

### Motivation

C2 smoke v0.1 showed that guidance learned in one context could be useful in another but hidden by single-category retrieval.

---

## Smoke Bomb transition guard

### Bug

After Smoke Bomb ended combat, CommunicationMod could briefly expose a stale command-ready combat snapshot. The controller could make an additional tactical decision and issue `PLAY` after the foreground screen had already transitioned.

### Fix

- Mark Smoke Bomb escape as pending.
- Suppress tactical decisions on bounded stale combat snapshots.
- Clear immediately when the game leaves combat.
- Release after a bounded number of waits to avoid deadlock.

Validated during B2 smoke v0.2 before final official collection.

---

## C2 smoke v0.2

- Two valid runs.
- Six final human-guided lessons.
- Complete source coverage.
- No current/future leakage.
- Live cross-category retrieval verified.
- Human feedback demonstrated correction of causal emphasis.
- Exposed the Smoke Bomb transition edge case.

---

## B2 smoke v0.2

- Two valid autonomous runs.
- Six raw lessons.
- Seven playbook rules.
- Complete source coverage.
- No current/future leakage.
- Live cross-category retrieval verified.
- Smoke Bomb guard exercised successfully.

---

## C2 smoke v0.1 — trajectory-level feedback

### Added

- Browser-based review through `reflection/feedback_app.py`.
- Run summary, flagged review candidates, strategic timeline, compact trajectory, and initial reflection.
- Natural-language trajectory feedback.
- Permanent raw memory and cumulative playbook update.

### Finding

Single-category playbook retrieval was insufficient for multi-context strategic guidance. This motivated `applies_to` and cumulative-playbook-v2.

---

## B2/C2 cumulative-memory architecture

### Added

- Permanent raw lesson banks.
- Cumulative playbook consolidation.
- `source_memory_ids` provenance.
- Full source-coverage validation.
- Isolated smoke/official files.
- Matched seed protocol.

### Research decision

B2 and C2 share the stronger memory interface so the human-feedback treatment is not confounded by different memory capacity.

---

## Condition C1 complete

- 30 reviewed runs.
- 73 retained final lessons.
- 61 accepted, 11 corrected, 1 added.
- Demonstrated that human review can correct wrong causal interpretation, missing context, vague rules, and false lessons.
- Still inherited B's top-3 exact-category retrieval limitation.

---

## Condition B complete

- 30 valid autonomous self-reflection runs.
- 85 stored lessons.
- Mean floor 27.23 vs baseline 23.37.
- Mean score 236.63 vs baseline 200.43.
- Card-reward skip rate increased from 2.8% to 14.1%.
- Low-HP campfire behavior became substantially more conservative.
- No wins and no completed three-key plan.
- Exposed memory repetition, rolling-window loss, and long-horizon planning limits.

### Watchdog fix

One interrupted physical run showed that `ready_for_command=false` must not end watchdog recovery. Polling was changed to continue until command-ready state.

---

## Condition A baseline complete

- 30 valid runs with no cross-run learning.
- Mean floor 23.37.
- Mean score 200.43.
- 0 wins.
- Established mid-Act-2 attrition, deck growth, low-HP smithing, and resource timing as recurring strategic issues.

---

## Controller stabilization before experiments

Major additions included:

- generic events;
- rest sites and smith follow-up selection;
- shops and removal;
- treasure rooms;
- boss relics;
- potion use/replacement;
- HAND_SELECT/GRID_SELECT;
- terminal-state caching;
- map decoding;
- controller-side key tracking;
- structured JSONL event logging;
- watchdog/state recovery.
