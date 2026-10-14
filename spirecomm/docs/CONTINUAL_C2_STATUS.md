# Continual C2 Status

> **Last finalized run:** 33  
> **Current Ascension:** 0  
> **Next intended run:** 34  
> **Next controller:** `c2-continual-teaching-v1.2.1-applicability-recency-hotfix`

This file is the concise live status page for the open-ended continual C2 phase. It should be updated at meaningful checkpoints or controller boundaries rather than after every minor code change.

## Controlled experiment already completed

The matched B2/C2 experiment is complete and frozen. Its headline result was better progression under authoritative human teaching:

| Metric | B2 autonomous | C2 human-taught |
|---|---:|---:|
| Runs | 15 | 15 |
| Wins | 0 | 0 |
| Mean floor | 18.73 | 27.33 |
| Median floor | 16 | 23 |
| Best floor | 29 | 50 |
| Mean score | 144.60 | 251.47 |
| Act 2+ | 6/15 | 13/15 |
| Act 3 | 0/15 | 2/15 |

Paired matched-seed direction:

- C2 higher floor on 11/15 seeds;
- C2 higher score on 10/15 seeds;
- mean paired gain: `+8.60` floors and `+106.87` score.

The continual phase must not be pooled into this controlled comparison.

## Continual phase chronology

### Runs 16–28

Architecture: original continual C2 wrapper, inherited one-action decision structure.

Main observation: continued human teaching improved the amount and specificity of strategic memory, but persistent card-selection and combat-ordering errors remained. By Run 28, the dominant limitation appeared to be execution/planning rather than a lack of feedback text.

Checkpoint:

```text
spirecomm/runs/C2_continual_v1_0_through_run28/
```

### Runs 29–32

Architecture:

```text
c2-continual-teaching-v1.1.1-card-prior-turn-planner
```

Added expert card priors and explicit turn planning. Card-reward reasoning became more inspectable and Skip was considered explicitly.

However, the combat planner executed only the first planned action and then called the model again from scratch. Run 32 demonstrated the resulting inconsistency: a planned defensive follow-up could be abandoned immediately after the first setup action.

Run-32 result:

- LOSS;
- Act 1 Floor 16;
- score 106;
- death: Hexaghost.

Pre-v1.2 checkpoint:

```text
spirecomm/runs/C2_continual_through_run32_pre_v1_2/
```

Checkpoint validation:

- completed/reflected runs: 32;
- raw lessons: 46;
- playbook rules: 32;
- feedback rows: 32.

### Run 33

Architecture:

```text
c2-continual-teaching-v1.2.0-persistent-planning
persistent-deck-plan+sticky-turn-plan+focused-memory-v1
```

Result:

- LOSS;
- Act 2 Floor 33;
- score 292;
- death: Collector;
- final keys: none;
- final deck size: 26.

What improved:

- sticky combat sequences were actually followed;
- draw-changing actions could intentionally stop a plan and trigger replanning;
- the card evaluator maintained an explicit deck plan;
- late reward decisions showed more willingness to Skip;
- high-frequency combat prompts were reduced to a focused subset instead of the full applicable playbook.

What remained weak:

- the deck plan sometimes identified long-term scaling as the dominant weakness but still selected a locally efficient attack instead of the offered scaling tool;
- card-addition thresholds were still occasionally too permissive once the deck was already reasonably complete;
- focused-memory ranking could omit a recent authoritative cross-category lesson.

Run-33 human teaching therefore focused on:

1. obeying the strategic bottleneck identified by the deck plan rather than preferring a merely efficient local upgrade;
2. raising the bar for adding cards as the deck matures;
3. retaining the improved sticky combat sequencing while using the cheapest sufficient defensive resource based on actual mitigation.

## Run-33 retrieval issue and Run-34 hotfix

Run-32 authoritative teaching was stored correctly as:

```text
primary category = CARD_REWARD
applies_to = [CARD_REWARD, COMBAT]
authoritative = true
```

Under v1.2.0, it was eligible for combat retrieval but could be pushed below the 8-rule combat cutoff because exact primary-category match ranked ahead of recency.

The Run-34 hotfix changes ranking to prioritize:

```text
authoritative status
-> source-run recency
-> primary-category match
-> GENERAL tie-break
```

while preserving `applies_to` as the eligibility filter.

Next controller:

```text
spirecomm/test_connection_c2_continual_v1_2_1.py
```

Expected marker:

```text
c2-continual-teaching-v1.2.1-applicability-recency-hotfix
```

## Active research interpretation

The continual phase now supports a useful secondary finding:

> Accumulating human teaching exposed execution and planning limits that could not be solved by adding more textual feedback alone.

This is why the longitudinal phase contains explicit architecture interventions. Those interventions should be analyzed descriptively by controller era, not treated as if every continual run came from one frozen policy.

## Next checklist

Before Run 34:

- confirm Run 33 has `POST_RUN_REFLECTION_COMPLETE`;
- confirm playbook is updated through Run 33;
- activate `test_connection_c2_continual_v1_2_1.py` as `test_connection.py`;
- compile it;
- preflight the controller marker and active agent class;
- only then start Run 34.
