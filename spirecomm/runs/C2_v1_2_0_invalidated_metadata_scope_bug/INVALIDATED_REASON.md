# C2 v1.2.0 — Invalidated Metadata-Scope Attempt

## Status

**INVALIDATED — do not include this attempt in the final matched C2 analysis.**

The preserved attempt contains one completed official C2 run (seed `260925001`) and a partial second run (seed `260925002`).

## Reason for invalidation

Run 1 used the C2 v1.2.0 authoritative-human-teaching path correctly and stored the human review verbatim.

However, the metadata-only organizer tagged human teaching that explicitly discussed **Neow's blessing** as:

- primary category: `EVENT`
- `applies_to`: `EVENT`, `REST`, `CARD_REWARD`, `SHOP`, `BOSS_REWARD`

The gameplay controller routes `NEOW_BLESSING` through the `GENERAL` retrieval category. Because `GENERAL` was absent, the Run-1 authoritative rule was not retrieved at Run 2's Neow decision even though the playbook had already been updated through Run 1.

The same rule was later retrieved at a Run-2 card-reward decision, confirming that storage and cross-run memory were functioning and that the failure was specifically retrieval-scope metadata.

## Resolution

C2 v1.2.1 added two protections:

1. the metadata prompt explicitly documents the controller's decision-category mapping, including `NEOW_BLESSING -> GENERAL`;
2. a deterministic safeguard adds `GENERAL` whenever authoritative human teaching explicitly mentions Neow or a starting-relic-to-boss-relic swap.

A dedicated two-run v1.2.1 scope smoke then **passed**: Run-1 authoritative Neow teaching was retrieved at Run-2 `NEOW_BLESSING` and the actor selected the boss-relic swap consistent with the teaching.

Official C2 collection was restarted from empty memory with v1.2.1 and completed all 15 matched runs.

Final C2 dataset:

```text
../C2_v1_2_1_15runs_final/
```

This v1.2.0 attempt remains preserved for provenance only.
