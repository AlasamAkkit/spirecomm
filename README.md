# Slay the Spire LLM Self-Reflection FYP

This repository contains a Final Year Project investigating whether a large-language-model (LLM) agent can improve at **Slay the Spire** through persistent cross-run memory, autonomous self-reflection, and iterative human teaching.

The project builds on `spirecomm` and ForgottenArbiter's CommunicationMod. A Python controller converts game states into a constrained legal action set, asks the LLM to choose among those legal actions, validates the choice, and sends the corresponding protocol command back to Slay the Spire.

## Research question

> To what extent can iterative human feedback improve the long-horizon decision-making of an LLM agent in Slay the Spire, compared with autonomous self-reflection under the same memory system?

## Current status

The controlled **B2 vs C2 matched-seed experiment is complete**.

- **B2 v1.1.1** is the autonomous self-reflection control.
- **C2 v1.2.1** is the final human-taught treatment used in the comparison.
- Both conditions used the same 15 seeds in the same order, the same actor model, Ironclad at Ascension 0, the same legal-action/controller interface, and the same cumulative-playbook-v2 memory mechanism.
- C2 differed by adding authoritative human review after each completed run.

C2 outperformed B2 on progression and score, although neither condition achieved a win.

| Metric | B2 v1.1.1 | C2 v1.2.1 |
|---|---:|---:|
| Runs | 15 | 15 |
| Wins | 0 | 0 |
| Mean floor | 18.73 | **27.33** |
| Median floor | 16 | **23** |
| Best floor | 29 | **50** |
| Mean score | 144.60 | **251.47** |
| Median score | 112 | **197** |
| Best score | 251 | **629** |
| Reached Act 2+ | 6/15 | **13/15** |
| Reached Act 3 | 0/15 | **2/15** |
| Final raw lessons | 38 | 25 |
| Final playbook rules | 14 | 17 |

Paired across the same seeds:

- C2 reached a higher floor on **11/15** seeds; B2 did so on 4/15.
- Mean paired floor difference: **+8.60 floors for C2**.
- C2 achieved a higher score on **10/15** seeds; B2 did so on 5/15.
- Mean paired score difference: **+106.87 points for C2**.

The strongest defensible conclusion is that authoritative human teaching substantially improved **survival and long-horizon progression**, especially by reducing early-game failures and enabling later-Act play, but did not yet solve the full game.

## Experimental progression

| Condition | Cross-run learning | Status |
|---|---|---|
| **A — Baseline** | None | Complete — 30 valid runs |
| **B — Self-reflection** | LLM reflection; newest matching memories, max 3 | Complete — 30 valid runs |
| **C1 — Human-curated reflection** | Human accepts/corrects/rejects/adds structured lessons before storage | Complete — 30 reviewed runs |
| **B2 — Autonomous cumulative-memory control** | LLM reflection -> permanent raw memory -> cumulative playbook | Complete — final v1.1.1 15-run control |
| **C2 — Authoritative human-taught system** | Initial reflection -> approve unchanged OR verbatim human teaching -> cumulative playbook | Complete — final v1.2.1 15-run treatment |

### Condition A

The 30-run no-memory baseline established the agent's starting capability.

- mean floor: 23.37
- median floor: 24
- mean score: 200.43
- Act 2: 20/30
- Act 3: 1/30
- wins: 0/30

### Condition B

Condition B added autonomous post-run reflection and newest-first exact-category retrieval, capped at three lessons.

- 85 stored self-generated lessons
- mean floor: 27.23
- median floor: 28
- mean score: 236.63
- Act 2: 22/30
- Act 3: 3/30
- wins: 0/30

Observed behavioural changes included substantially more card skipping and much more conservative low-HP campfire behaviour. The study also exposed two memory-system limitations: older lessons could age out of the active top-3 window, and single-category storage could hide useful cross-category guidance.

### Condition C1

C1 inserted human review before memory storage while retaining the B-era retrieval mechanism.

The final memory contains **73 retained human-curated lessons**:

- COMBAT: 30
- CARD_REWARD: 17
- REST: 12
- EVENT: 8
- SHOP: 4
- GENERAL: 1
- BOSS_REWARD: 1

Provenance among retained lessons: **61 accepted, 11 corrected, 1 human-added**. C1 showed that a structurally valid LLM lesson can still require human correction for causal attribution, context, specificity, or factual strategy.

### B2/C2 follow-up

The follow-up replaced rolling top-3 memory with **cumulative-playbook-v2** for both conditions.

Every final lesson is retained in raw memory. Playbook rules contain:

- one primary category;
- `applies_to` decision categories;
- `when`;
- `guidance`;
- `rationale`;
- confidence;
- `source_memory_ids`.

Every raw lesson ID must remain represented by at least one playbook rule. Retrieval scans the complete playbook and injects every applicable rule rather than only the newest three lessons.

## C2 authoritative human-teaching policy

C2 originally experimented with letting a second LLM rewrite human feedback. That design was removed before final collection because it introduced an additional source of strategic distortion.

Final C2 v1.2.1 uses two review outcomes:

1. **`APPROVE_INITIAL`** — store the initial LLM reflection lessons unchanged.
2. **`HUMAN_TEACHING`** — store the human's natural-language strategic teaching verbatim.

For authoritative human teaching, an LLM may assign retrieval metadata only: title, primary category, and `applies_to`. It may not paraphrase, summarize, correct, soften, expand, or otherwise rewrite the strategic content.

Authoritative human rules are reattached to the playbook deterministically, and validation requires actor-facing guidance to equal the stored human teaching exactly.

The final 15-run C2 batch used:

- 10 `HUMAN_TEACHING` reviews;
- 5 `APPROVE_INITIAL` reviews;
- 25 final raw lessons;
- 17 final playbook rules.

## Integrity and controller fixes

Several development runs were deliberately invalidated rather than silently included after correctness bugs were found.

Important fixes include:

- watchdog polling until CommunicationMod returns `ready_for_command=true`;
- controller-side key tracking when the installed CommunicationMod omitted key state;
- Smoke Bomb stale-transition guard;
- permanent card-reward skip guard preventing a skipped reward from reopening;
- cumulative-memory source-coverage validation;
- C2 v1.2.1 Neow retrieval-scope safeguard.

### Invalidated B2 v1.1.0

The first B2 cumulative-memory batch was invalidated because skipped permanent card rewards could reopen. The bug produced 92 skip decisions across 19 reward instances in 9 runs and materially altered deck construction. The corrected B2 v1.1.1 batch was restarted from empty memory.

### Invalidated C2 v1.2.0

The first authoritative C2 attempt was invalidated after Run-1 Neow teaching was stored correctly but its metadata omitted the `GENERAL` retrieval scope, so Run 2 did not retrieve it at `NEOW_BLESSING`. v1.2.1 added explicit controller-category mapping plus a deterministic Neow/start-relic scope safeguard. A dedicated scope smoke verified cross-run retrieval before final collection.

## Final C2 v1.2.1 integrity

The final C2 batch contains:

- exactly 15 starts and 15 completions;
- requested seeds `260925001` through `260925015` in order;
- 15 completed post-run reflections;
- 3,705 memory retrievals;
- zero detected current-run or future-run memory leakage;
- complete raw-memory-to-playbook source coverage;
- verbatim preservation of all authoritative human teaching.

One transient API 500 occurred and recovered on retry without substituting a gameplay action. Two LLM calls returned out-of-range action indexes and used the controller's deterministic index fallback; these are retained as model-output/protocol failures rather than silently rerunning affected trajectories.

## System architecture

```text
Slay the Spire
      |
      v
CommunicationMod JSON
      |
      v
Python controller
  - state parsing
  - legal-action generation
  - deterministic interactions
  - experiment logging
  - watchdog / transition guards
      |
      v
LLM actor
      |
      v
validated legal action
      |
      v
CommunicationMod command
      |
      v
Slay the Spire
```

Learning occurs through external memory, not model-weight training:

```text
completed run
    -> compact trajectory
    -> initial reflection
    -> B2: autonomous lessons
       C2: approve lessons OR verbatim human teaching
    -> permanent raw memory
    -> cumulative playbook
    -> applicable rules injected into later decisions
```

## Frozen datasets

Final datasets are stored under `spirecomm/runs/`:

- `baseline_v1_30runs_final/`
- `condition_b_self_reflection_30runs_final/`
- `condition_c_human_feedback_30_runs/`
- `B2_v1_1_1_15runs_final/`
- `C2_v1_2_1_15runs_final/`

Diagnostic and invalidated archives are retained separately for provenance and must not be mixed into final analyses.

The C2 Git archive currently contains the official structured event log and controller snapshots. The raw C2 memory/playbook/reflection-output files were Git-ignored during collection; they were separately validated during the final integrity audit and should be preserved outside the repository if full reflection-level reproducibility is required.

## Next research phase

The matched B2/C2 experiment is finished. The planned next phase is:

1. carry forward C2 as the selected learning architecture;
2. continue human-guided learning on **fresh, unseen training seeds**;
3. freeze the resulting controller + memory/playbook state;
4. evaluate the frozen agent on a separate set of **held-out unseen seeds** with feedback and memory updates disabled;
5. compare final generalization against appropriate frozen controls.

This separates **learning seeds** from **evaluation seeds** and avoids treating continued feedback on test trajectories as final evaluation.

## Documentation

Canonical research records are in `spirecomm/docs/`:

- `PROJECT_LOG.md` — project and methodological milestones;
- `EXPERIMENTS.md` — conditions, datasets, quantitative results, and protocols;
- `OBSERVATIONS.md` — stable observation/failure IDs;
- `CHANGELOG.md` — implementation and experiment changes;
- `FINAL_B2_C2_ANALYSIS.md` — final matched comparison and integrity summary.

`spirecomm/FOLLOWUP_B2_C2_FINAL_PROTOCOL.md` records the completed follow-up protocol and final status.

## Requirements

- Slay the Spire
- ModTheSpire
- BaseMod
- CommunicationMod
- Python with the local `spirecomm` package
- OpenAI Python SDK and an `OPENAI_API_KEY`

## Acknowledgement

The communication layer is based on the open-source `spirecomm` project and ForgottenArbiter's CommunicationMod. This FYP extends that base with the autonomous LLM controller, structured experimental logging, post-run reflection, persistent memory, human-feedback workflows, correctness safeguards, and comparative learning-study design.
