# FYP Research Documentation

This folder contains the maintained research and engineering records for the Slay the Spire LLM self-reflection / human-teaching FYP.

## Canonical files

- `PROJECT_LOG.md` — chronological architectural, methodological, and project milestones.
- `EXPERIMENTS.md` — experimental conditions, completed batches, quantitative results, integrity checks, and evaluation protocol.
- `OBSERVATIONS.md` — stable research observations and failure categories using IDs such as `OBS-079`.
- `CHANGELOG.md` — implementation changes to the controller, reflection pipeline, memory system, and experiment infrastructure.
- `FINAL_B2_C2_ANALYSIS.md` — final matched B2/C2 comparison, data-integrity summary, interpretation, and limitations.

The repository-level `README.md` provides the high-level project summary and current status.

## Source-of-truth rule

For a frozen experiment, the machine-readable source of truth is its structured event log stored with the archived experiment artifacts under `spirecomm/runs/`.

Do not manually edit experimental JSONL files after collection.

Active working logs, smoke-test memory, and live experiment memory must remain isolated from frozen datasets. Once a batch is accepted as final, freeze the selected controller and available research artifacts under a versioned directory in `spirecomm/runs/`.

## Documentation update rule

After a meaningful milestone:

1. record implementation changes in `CHANGELOG.md`;
2. add or update behavioural findings in `OBSERVATIONS.md`;
3. record experiment batches and controls in `EXPERIMENTS.md`;
4. add major architectural or methodological decisions to `PROJECT_LOG.md`;
5. freeze accepted experiment artifacts under `spirecomm/runs/<experiment_name>/`;
6. keep invalidated/debug datasets clearly separated from final datasets.

## Experimental progression

### Condition A — Baseline

- 30 valid Ironclad Ascension-0 runs.
- No cross-run memory.
- Mean floor 23.37; mean score 200.43; 0 wins.

### Condition B — Autonomous self-reflection

- 30 valid runs.
- `reflection-v0.2` generated at most three lessons after each run.
- Exact-category, newest-first retrieval capped at three lessons.
- 85 stored lessons.
- Mean floor 27.23; mean score 236.63; 0 wins.

### Condition C1 — Human-curated reflection

- 30 reviewed runs.
- Human ACCEPT/CORRECT/REJECT/ADD-style intervention before memory storage.
- 73 retained lessons: 61 accepted, 11 corrected, 1 added.
- Demonstrated that human review can correct strategically wrong or incomplete reflections, while still inheriting B's limited retrieval mechanism.

### B2/C2 matched follow-up

The follow-up replaced B/C1's rolling top-3 memory with `cumulative-playbook-v2` for both conditions.

- permanent raw memory;
- cumulative rules with `source_memory_ids`;
- cross-category `applies_to` scopes;
- validation requiring complete raw-memory source coverage;
- all applicable rules supplied to the actor.

#### B2 v1.1.1 — final autonomous control

- 15 matched seeds.
- 0 wins.
- Mean floor 18.73; median 16; best 29.
- Mean score 144.60; best 251.
- Act 2+: 6/15; Act 3: 0/15.
- 38 raw lessons; 14 final playbook rules.
- Zero current/future leakage across 2,924 retrievals.

#### C2 v1.2.1 — final authoritative human-taught treatment

- 15 matched seeds, identical order to B2.
- 0 wins.
- Mean floor 27.33; median 23; best 50.
- Mean score 251.47; median 197; best 629.
- Act 2+: 13/15; Act 3: 2/15.
- 25 raw lessons; 17 final playbook rules.
- 10 `HUMAN_TEACHING` reviews and 5 `APPROVE_INITIAL` reviews.
- Zero current/future leakage across 3,705 retrievals.
- All authoritative human teaching preserved verbatim through raw memory and actor-facing playbook guidance.

Paired result:

- C2 higher floor on 11/15 matched seeds, mean paired gain +8.60 floors.
- C2 higher score on 10/15 matched seeds, mean paired gain +106.87 points.

## Important invalidated/development batches

- `B2_v1_1_0_invalidated_card_skip_bug/` — invalidated because skipped permanent card rewards could reopen.
- `C2_v1_1_0_interrupted_card_skip_bug/` — interrupted before the same reward-flow fix.
- `C2_v1_2_0_invalidated_metadata_scope_bug/` — authoritative teaching stored correctly, but Neow guidance lacked `GENERAL` retrieval scope and was not retrieved at the next run's Neow decision.
- B2/C2 smoke archives — infrastructure/memory validation only; never mix with final result sets.

## Final C2 teaching design

C2 v1.2.1 separates strategy from indexing metadata.

- `APPROVE_INITIAL`: store the initial LLM lessons unchanged.
- `HUMAN_TEACHING`: store the human's natural-language guidance verbatim.
- A metadata-only LLM may infer title, category, and `applies_to`.
- It may not rewrite the strategic content.
- Authoritative rules are reconstructed deterministically from raw memory.

This makes the final treatment a direct test of human teaching rather than human feedback filtered through a second strategic reviser.

## Current project status

The controlled B2/C2 comparison is **complete** and C2 is the architecture selected to carry forward.

The next research phase should use fresh training seeds for continued C2 learning, then freeze the learned memory/playbook and evaluate on a separate held-out seed set with feedback and memory updates disabled.

## Archive note

`spirecomm/runs/C2_v1_2_1_15runs_final/` currently contains the committed official event log and controller snapshots. The raw C2 memory, playbook, and reflection-output files were Git-ignored during collection; they were separately validated in the final integrity audit and should be preserved externally if full reflection-level reproducibility is required.

## Central research question

> To what extent can iterative human feedback improve the long-horizon decision-making of an LLM agent in Slay the Spire, compared with autonomous self-reflection under the same memory system?
