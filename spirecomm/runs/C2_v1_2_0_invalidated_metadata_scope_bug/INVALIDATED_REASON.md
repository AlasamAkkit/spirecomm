# C2 v1.2.0 — Invalidated Metadata-Scope Attempt

## Status

**INVALIDATED — do not include this attempt in the final matched C2 analysis.**

The preserved attempt contains one completed official C2 run (seed `260925001`) and a partial second run (seed `260925002`).

## Reason for invalidation

Run 1 used the C2 v1.2.0 authoritative-human-teaching path correctly and stored the human review verbatim.

However, the metadata-only organizer tagged a human teaching that explicitly discussed **Neow's blessing** as:

- primary category: `EVENT`
- `applies_to`: `EVENT`, `REST`, `CARD_REWARD`, `SHOP`, `BOSS_REWARD`

The gameplay controller routes `NEOW_BLESSING` decisions through the `GENERAL` retrieval category. Because `GENERAL` was absent, the Run-1 authoritative rule was not retrieved at Run 2's Neow decision even though the playbook had already been updated through Run 1.

The same rule was subsequently retrieved at a Run-2 `CARD_REWARD` decision, confirming that storage and cross-run retrieval were functioning and that the failure was specifically retrieval-scope metadata.

## Resolution

C2 v1.2.1 adds two protections:

1. the metadata prompt explicitly documents the controller's decision-category mapping, including `NEOW_BLESSING -> GENERAL`;
2. a deterministic safeguard adds `GENERAL` whenever authoritative human teaching explicitly mentions Neow or a starting-relic-to-boss-relic swap.

Before restarting the official 15-run C2 collection, a dedicated two-run scope smoke must demonstrate that Run-1 Neow teaching is retrieved at Run-2 `NEOW_BLESSING`.

The invalidated attempt remains preserved for provenance only.
