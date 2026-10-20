# Slay the Spire LLM Human-Teaching FYP

This repository contains a Final Year Project studying whether an LLM agent can improve at **Slay the Spire** through persistent cross-run memory, autonomous self-reflection, and iterative authoritative human teaching.

The project builds on `spirecomm` and ForgottenArbiter's CommunicationMod. A Python controller converts game state into constrained legal actions, sends the relevant state/memory to the LLM, validates the response, and issues the resulting command back to the game.

## Research question

> To what extent can iterative human feedback improve the long-horizon decision-making of an LLM Slay the Spire agent compared with autonomous self-reflection under the same external-memory system?

## Current status

Two research stages are now separated explicitly.

### 1. Controlled B2 vs C2 experiment — complete

The final matched-seed experiment compared:

- **B2 v1.1.1:** autonomous self-reflection control;
- **C2 v1.2.1:** authoritative human-teaching treatment.

Both used the same 15 seeds in the same order, GPT-5.6 Luna, Ironclad at Ascension 0, the same legal-action interface, and the same cumulative-playbook-v2 memory architecture.

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
| Act 2+ | 6/15 | **13/15** |
| Act 3 | 0/15 | **2/15** |

Paired across identical seeds:

- C2 reached a higher floor on **11/15** seeds;
- mean paired floor gain: **+8.60**;
- C2 achieved a higher score on **10/15** seeds;
- mean paired score gain: **+106.87**.

Supported conclusion:

> Authoritative human teaching materially improved survival depth and long-horizon progression relative to autonomous self-reflection under the matched cumulative-memory design, although neither condition solved the game.

Canonical controlled-phase documents:

- [`spirecomm/docs/protocols/B2_C2_FINAL_PROTOCOL.md`](spirecomm/docs/protocols/B2_C2_FINAL_PROTOCOL.md)
- [`spirecomm/docs/FINAL_B2_C2_ANALYSIS.md`](spirecomm/docs/FINAL_B2_C2_ANALYSIS.md)

### 2. Continual C2 teaching — fixed-controller evaluation starting

After the matched experiment, C2 continued with accumulated human teaching, independent seeds and explicit **architecture interventions** (Runs 16–36). A fixed-controller human-feedback evaluation phase now starts at Run 37; it must not be pooled into the controlled B2/C2 matched analysis.

**Verified status at stable activation (October 2026):**

```text
Latest finalized and reflected run: 36
Raw lessons: 50
Cumulative playbook rules: 36
Current Ascension: 0
Run 37: in progress (outcome not yet available)
Fixed gameplay controller for Runs 37+: c2-continual-teaching-v1.4.0-stable-feedback-loop
Stable activation: PASS; 10/10 deterministic regression tests passed
```

| Runs | Controller | Main purpose |
|---|---|---|
| 16–28 | v1.0 continual | Human-teaching memory with one-action decisions |
| 29–32 | v1.1.1 | Expert card priors and proposed whole-turn plans; replan after every action |
| 33 | v1.2.0 | Run-level deck plan, sticky combat sequence, top-k memory |
| 34 | v1.2.1 | Fixed eligibility/recency ranking within top-k |
| 35 | v1.3.0 | No-top-k cumulative memory, context pinning, independent combat verifier |
| 36 | v1.3.1 | Frail/Dexterity-aware known Block projection |
| 37+ | **v1.4.0 stable** | Cross-encounter plan invalidation, end-turn guard, fixed-code feedback evaluation |

**The critical research distinction:** the controlled B2/C2 experiment tests human teaching under matched conditions; Runs 16–36 exposed and addressed controller limitations; Runs 37+ are designed to hold the controller fixed so human teaching can be studied without continual code changes.

Start with:
- [Stable feedback workflow](spirecomm/docs/C2_STABLE_FEEDBACK_WORKFLOW.md)
- [Full architecture and issue retrospective](spirecomm/docs/SYSTEM_ARCHITECTURE_AND_RETROSPECTIVE.md)
- [Runs 33–37 ledger](spirecomm/docs/CONTINUAL_RUN_LEDGER_33_37.md)
- [Current status](spirecomm/docs/CONTINUAL_C2_STATUS.md)
- [Controller provenance](spirecomm/docs/CONTROLLER_HISTORY.md)

## Experimental progression

| Condition / phase | Learning mechanism | Status |
|---|---|---|
| A baseline | none | 30 valid runs, frozen |
| B self-reflection | LLM reflection + newest matching memories, max 3 | 30 valid runs, frozen |
| C1 human-curated reflection | human accepts/corrects/rejects/adds lessons | 30 reviewed runs, frozen |
| B2 autonomous cumulative memory | autonomous reflection -> raw memory -> cumulative playbook | final 15-run matched control, frozen |
| C2 authoritative human teaching | approve initial lessons OR verbatim human teaching -> same playbook architecture | final 15-run matched treatment, frozen |
| Continual C2 | persistent human teaching with explicit controller interventions | active; finalized through Run 36; Run 37 in progress |

## Architecture

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
  - deterministic interactions / safety guards
  - experiment logging
  - memory retrieval
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

Learning occurs through **external memory**, not model-weight updates.

```text
completed run
 -> trajectory
 -> initial reflection
 -> human review / autonomous finalization
 -> permanent raw memory
 -> indexed playbook
 -> later decision prompts
```

The continual v1.2 architecture additionally maintains a persistent run-level deck plan and sticky within-turn combat plan.

## Authoritative human teaching

C2 uses `authoritative-human-teaching-v1`.

A review ends as either:

- `APPROVE_INITIAL` — store the initial reflection lessons unchanged; or
- `HUMAN_TEACHING` — store the human's natural-language strategy verbatim.

For human teaching, an LLM may infer retrieval metadata such as title, primary category, and `applies_to`, but may not rewrite the strategic content.

## Repository map

```text
README.md                         project overview
spirecomm/                        runtime/controller code and experiment logs
spirecomm/docs/                   canonical research documentation
spirecomm/docs/protocols/         frozen and active experiment protocols
spirecomm/runs/                   frozen/diagnostic run archives
reflection/                       raw memory, playbook, feedback, priors, reflection outputs
```

Start with:

- [`spirecomm/docs/README.md`](spirecomm/docs/README.md) — documentation index;
- [`spirecomm/docs/REPO_FILE_GUIDE.md`](spirecomm/docs/REPO_FILE_GUIDE.md) — file/layout guide;
- [`spirecomm/runs/README.md`](spirecomm/runs/README.md) — archive guide;
- [`reflection/README.md`](reflection/README.md) — memory/reflection artifacts.

## Frozen datasets

Final controlled datasets under `spirecomm/runs/` include:

- `baseline_v1_30runs_final/`
- `condition_b_self_reflection_30runs_final/`
- `condition_c_human_feedback_30_runs/`
- `B2_v1_1_1_15runs_final/`
- `C2_v1_2_1_15runs_final/`

Important continual checkpoints include:

- `C2_continual_v1_0_through_run28/`
- `C2_continual_through_run32_pre_v1_2/`

Invalidated and smoke archives remain in the repository for provenance and must not be mixed into final controlled analyses.

## Requirements

- Slay the Spire
- ModTheSpire
- BaseMod
- CommunicationMod
- Python with the local `spirecomm` package
- OpenAI Python SDK
- `OPENAI_API_KEY`

## Acknowledgement

The communication layer is based on the open-source `spirecomm` project and ForgottenArbiter's CommunicationMod. This FYP extends that base with an LLM controller, structured experimental logging, post-run reflection, persistent memory, human-teaching workflows, correctness guards, controller-version provenance, and comparative/longitudinal study design.
