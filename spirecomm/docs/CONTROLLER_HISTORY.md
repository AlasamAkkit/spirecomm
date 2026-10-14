# Controller and Intervention History

This file is the canonical map from experimental runs to controller versions. The repository intentionally preserves historical controllers for reproducibility.

## Controlled phases

| Phase | Runs | Controller / version | Status | Notes |
|---|---:|---|---|---|
| A baseline | 30 | baseline controller | Frozen | No cross-run learning |
| B self-reflection | 30 | reflection-v0.2 + original retrieval | Frozen | Autonomous memory, exact-category newest-3 retrieval |
| C1 human feedback | 30 | original human-curated memory | Frozen | Human review, same limited retrieval structure |
| B2 invalid | 15 | B2 v1.1.0 | Invalidated | Permanent card Skip/reopen bug |
| B2 final | 15 | B2 v1.1.1 | Frozen | Final autonomous cumulative-memory control |
| C2 invalid | partial | C2 v1.2.0 | Invalidated | Metadata scope bug at Neow |
| C2 final | 15 | C2 v1.2.1 | Frozen | Final authoritative-human-teaching treatment |

Canonical controlled-phase analysis uses only:

```text
spirecomm/runs/B2_v1_1_1_15runs_final/
spirecomm/runs/C2_v1_2_1_15runs_final/
```

## Continual C2 phase

| Run range | Controller marker | Decision architecture | Experimental use |
|---|---|---|---|
| 16–28 | `c2-continual-teaching-v1.0` | inherited one-action architecture | Used |
| 29–32 | `c2-continual-teaching-v1.1.1-card-prior-turn-planner` | expert card priors + permanent reward scorer + whole-turn proposal followed by fresh replanning after each action | Used |
| 33 | `c2-continual-teaching-v1.2.0-persistent-planning` | persistent deck plan + sticky turn plan + focused memory v1 | Used |
| 34+ | `c2-continual-teaching-v1.2.1-applicability-recency-hotfix` | persistent deck plan + sticky turn plan + focused memory v1.1 | Next / active target |

## Controller files

### `test_connection_c2_continual_v1.py`

Introduced open-ended continual C2 teaching after the 15-run matched experiment.

Responsibilities:

- loads the frozen final C2 controller;
- preserves C2 memory across future runs;
- provides persistent fresh-seed scheduling;
- persists Ascension progression;
- reconstructs progress after restart.

Used for Runs 16–28.

### `test_connection_c2_continual_v1_1.py`

Development controller that introduced:

- expert Ironclad card priors;
- explicit permanent card-reward scoring;
- turn-level combat planning.

It contained an activation bug: the inherited main loop still constructed the previously rebound base agent class, so merely replacing `prior.ContinualC2Agent` did not guarantee that the v1.1 subclass was instantiated.

Do not use this file directly as evidence that v1.1 gameplay was active.

### `test_connection_c2_continual_v1_1_1.py`

Activation hotfix for v1.1.

It explicitly rebinds the full inherited construction path so the main CommunicationMod loop creates `ContinualC2V11Agent`.

Used for Runs 29–32.

### `test_connection_c2_continual_v1_1_2.py`

Development-only human-authority wrapper.

It experimented with:

- explicit decision-authority precedence;
- deterministic enforcement of narrow unconditional human card prohibitions.

Its proposed intervention boundary became stale before activation. No completed continual run should be attributed to this version.

**Status: developed, unused.**

### `test_connection_c2_continual_v1_2.py`

Persistent-planning intervention beginning at Run 33.

Adds:

- persistent run-level deck plan;
- card scores conditioned on deck goals/weaknesses;
- deterministic argmax card selection with Skip winning ties;
- sticky within-turn combat sequences;
- focused memory windows for high-frequency tactical decisions.

Used for Run 33.

### `test_connection_c2_continual_v1_2_1.py`

Focused-memory applicability/recency hotfix intended from Run 34 onward.

Run 33 exposed that v1.2.0 could omit a recent authoritative cross-category lesson because exact primary-category match ranked ahead of recency. v1.2.1 keeps applicability as the candidate filter, then ranks authoritative applicable teaching by recency before primary-category metadata.

Marker:

```text
c2-continual-teaching-v1.2.1-applicability-recency-hotfix
```

Memory policy:

```text
focused_authority_applicability_recent_v1
```

## Finalize-only wrappers

### `test_connection_c2_finalize_run32.py`

Loads the exact controller that played Run 32 and caps the session at 32 completed runs. It allows pending human feedback/reflection to finish without accidentally starting Run 33.

### `test_connection_c2_finalize_run33.py`

Same purpose for the Run-33 → Run-34 boundary. It loads v1.2.0, permits Run 33 finalization, and prevents Run 34 from starting before the v1.2.1 hotfix is activated.

## Checkpoint scripts and archives

### Through Run 28

```text
spirecomm/runs/C2_continual_v1_0_through_run28/
```

Marks the end of the original continual one-action architecture.

### Through Run 32, before v1.2

```text
spirecomm/freeze_c2_run32_checkpoint.py
spirecomm/runs/C2_continual_through_run32_pre_v1_2/
```

Validated checkpoint values:

- completed/reflected runs: 32;
- raw lessons: 46;
- playbook rules: 32;
- feedback rows: 32.

### Through Run 33, before v1.2.1

Freeze script:

```text
spirecomm/freeze_c2_run33_checkpoint.py
```

Expected archive after running the script locally:

```text
spirecomm/runs/C2_continual_through_run33_pre_v1_2_1/
```

The script validates:

- exactly RUN_END 1–33;
- exactly POST_RUN_REFLECTION_COMPLETE 1–33;
- Run 33 controller marker is v1.2.0 persistent planning;
- playbook updated through Run 33;
- complete raw-memory-to-playbook source coverage;
- finalized Run-33 review/final-reflection artifacts.

This checkpoint should be created before Run 34 begins.

## Provenance rule

When reporting a run, use the controller marker recorded in that run's structured event log. Never infer controller version from the current contents of `test_connection.py`, because that file is intentionally replaced as the active entry point changes.
