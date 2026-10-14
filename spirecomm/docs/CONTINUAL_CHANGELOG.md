# Continual C2 Changelog

This changelog continues the original `CHANGELOG.md` for the post-controlled, open-ended continual-C2 phase.

## 2026-10-14 — Run 33 finalized; v1.2.1 retrieval hotfix prepared

### Run 33

- Finalized Run 33 under `c2-continual-teaching-v1.2.0-persistent-planning`.
- Outcome: LOSS, Act 2 Floor 33, score 292, Collector.
- Confirmed persistent deck-plan generation.
- Confirmed deterministic card-reward argmax selection with Skip exact-tie preference.
- Confirmed sticky combat plans are followed across multiple actions.
- Confirmed draw-changing steps can intentionally stop a plan and trigger fresh planning.

### Focused-memory audit

- Verified Run-32 authoritative teaching was stored correctly as primary `CARD_REWARD` with `applies_to = [CARD_REWARD, COMBAT]`.
- Found v1.2.0 ranking bug: exact primary-category match ranked ahead of recency, allowing older COMBAT-primary rules to fill the top-8 window before the newer cross-category authoritative lesson.
- Added `test_connection_c2_continual_v1_2_1.py`.
- New memory policy: `focused_authority_applicability_recent_v1`.
- Run-34+ ranking now prioritizes authority and source-run recency before primary-category metadata.

### Safe Run-33 finalization

- Added `test_connection_c2_finalize_run33.py`.
- Wrapper loads the exact v1.2.0 gameplay controller and caps completed runs at 33.
- This allows Run-33 human review/reflection to complete without accidentally starting Run 34 under v1.2.0.

### Documentation reorganization

- Created canonical protocol directory: `docs/protocols/`.
- Added canonical frozen matched protocol: `B2_C2_FINAL_PROTOCOL.md`.
- Added canonical active continual protocol: `C2_CONTINUAL_TEACHING_PROTOCOL.md`.
- Added `CONTROLLER_HISTORY.md`.
- Added `CONTINUAL_C2_STATUS.md`.
- Added `CONTINUAL_OBSERVATIONS.md` beginning at OBS-089.
- Added current learning/feedback/logging/repository reference docs.
- Converted old root-level protocol files to compatibility pointers.
- Updated repository and archive README files to remove the superseded fixed held-out Phase III plan.

## 2026-10-13 to 2026-10-14 — Run 33 persistent-planning intervention

### v1.2.0 controller

Added `test_connection_c2_continual_v1_2.py` with intervention start Run 33.

New architecture:

```text
persistent-deck-plan+sticky-turn-plan+focused-memory-v1
```

Changes:

- run-level persistent deck plan for permanent reward evaluation;
- deck plan tracks offense, defense, scaling, draw/energy, AoE, weaknesses, priorities, avoid-list, and add policy;
- permanent reward model returns scores rather than an independent free-form final choice;
- controller deterministically chooses numerical argmax; Skip wins ties;
- sticky within-turn action sequences replace unconditional replan-after-every-action behavior;
- focused tactical memory limits COMBAT to 8 rules and CARD_REWARD to 10 rules.

### Pre-v1.2 checkpoint

Added `freeze_c2_run32_checkpoint.py` and froze:

```text
spirecomm/runs/C2_continual_through_run32_pre_v1_2/
```

Validation:

- completed/reflected runs: 32;
- raw lessons: 46;
- playbook rules: 32;
- feedback rows: 32.

## Run 32 — architecture failure identified

- Run 32 ended LOSS, Act 1 Floor 16, score 106, Hexaghost.
- Persistent issues remained in deck building and combat action order.
- Critical trace: model initially planned setup followed by defense, executed the setup, then the next fresh planning call abandoned the defensive follow-up and chose damage instead.
- Concluded that the v1.1.1 turn planner was behaviorally still a one-action architecture because it discarded the rest of its own plan after every action.
- Human teaching emphasized coherent long-term deck planning and preserving full-turn sequences unless the game state materially changes.

## Runs 29–32 — expert priors and first turn-planner intervention

### Card priors

Added `reflection/ironclad_card_priors.json` with fixed expert-quality priors for 72 non-starter Ironclad cards.

Priors are advisory evidence only and can be overridden by deck context, synergy, human teaching, boss/Act context, or Skip.

### v1.1 controller

Added card-reward evaluation and whole-turn combat reasoning.

### v1.1 activation bug

Found that the inherited main loop still instantiated the previously rebound base agent, so the new subclass could silently fail to activate.

### v1.1.1 activation hotfix

Added `test_connection_c2_continual_v1_1_1.py` to explicitly rebind the full construction path.

Runs 29–32 use:

```text
c2-continual-teaching-v1.1.1-card-prior-turn-planner
```

## Run 29 — first verified v1.1.1 run

- LOSS, Act 2 Floor 33, score 328, Bronze Automaton.
- 203 combat planner calls, 0 combat fallbacks.
- 16 permanent card-evaluator calls, 0 card fallbacks.
- Confirmed explicit Skip scoring and deck-context reasoning.

## Through Run 28 — end of original continual v1.0 era

Frozen checkpoint:

```text
spirecomm/runs/C2_continual_v1_0_through_run28/
```

Run-28 feedback identified recurring problems with:

- card selection;
- lack of coherent build planning;
- defense when enemies were not attacking;
- attack-before-Vulnerable ordering;
- general combat sequencing.

This evidence motivated the first post-controlled architecture intervention rather than simply adding more feedback text.
