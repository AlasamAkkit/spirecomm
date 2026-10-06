# Research Observations

This file distinguishes controller/interface limitations from genuine reasoning and memory failures. Observation IDs are stable and should not be renumbered.

| ID | Observation | Category | Status |
|---|---|---|---|
| OBS-001 | Generic event screens were initially unsupported. | CONTROLLER_GAP | Resolved |
| OBS-002 | High-level decisions can create secondary card-selection screens. | CONTROLLER_GAP | Resolved |
| OBS-003 | Rest sites require a separate decision interface. | CONTROLLER_GAP | Resolved |
| OBS-004 | Smith requires card selection followed by confirmation. | INTERFACE_GAP | Resolved |
| OBS-005 | Completed rest-site actions can still require `PROCEED`. | INTERFACE_GAP | Resolved |
| OBS-006 | Merchant interaction contains multiple screen states. | CONTROLLER_GAP | Resolved |
| OBS-007 | Merchant exit can produce a re-entry loop without short-term controller memory. | MEMORY_GAP | Resolved |
| OBS-008 | Treasure rooms require a multi-stage interaction sequence. | CONTROLLER_GAP | Resolved |
| OBS-009 | Combat cards can generate nested HAND_SELECT decisions. | CONTROLLER_GAP | Resolved |
| OBS-010 | Multi-card selections must be handled sequentially across refreshed states. | INTERFACE_GAP | Resolved |
| OBS-011 | Strategic and deterministic actions should be separated to avoid unnecessary LLM calls. | EFFICIENCY | Ongoing |
| OBS-012 | Card information supplied to the LLM does not include complete semantic card-effect descriptions. | OBSERVATION_GAP | Open |
| OBS-013 | Boss relic rewards use a separate `BOSS_REWARD` state. | CONTROLLER_GAP | Verified |
| OBS-014 | Terminal states can lose useful final gameplay context; evaluation needs cached state plus GAME_OVER handling. | EVAL_INFRA | Resolved |
| OBS-015 | The early combat action space excluded potion usage, making some apparent failures unfair to attribute to the LLM. | ACTION_SPACE_GAP | Resolved |
| OBS-016 | Environment-interface coverage can be audited separately from gameplay quality. | EVAL_INFRA | Resolved |
| OBS-017 | Full controller coverage operated across repeated autonomous runs with no persistent unhandled-state blocker. | EVAL_INFRA | Observed |
| OBS-018 | Boss relic selection and inter-Act transition work in live gameplay. | INTERFACE_GAP | Verified |
| OBS-019 | Potion use and full-slot potion replacement work in live gameplay. | INTERFACE_GAP | Verified |
| OBS-020 | Numeric map action indexes are ambiguous with map x-coordinates; the LLM sometimes returned a coordinate instead of the requested index. | INTERFACE_GAP | Resolved |
| OBS-021 | The installed CommunicationMod build omitted `game_state.keys`; controller-side key tracking was required. | OBSERVATION_GAP | Resolved |
| OBS-022 | Baseline performance was bottlenecked mainly by mid-Act-2 attrition/risk management rather than controller failure. | REASONING_GAP | Observed in A |
| OBS-023 | Baseline card rewards were rarely skipped, making deck growth/selectivity a recurring strategic issue. | REASONING_GAP | Changed in B |
| OBS-024 | Low-HP campfire smithing before dangerous fights suggested weak resource preservation. | REASONING_GAP | Changed in B |
| OBS-025 | Autonomous reflection can generate useful lessons but also plausible, overgeneralized, or factually wrong lessons. | MEMORY_GAP | Verified |
| OBS-026 | Reflection can overfocus on the final combat rather than an earlier causal deck/resource decision. | MEMORY_GAP | Persisted |
| OBS-027 | Reflection can exhibit hindsight/temporal leakage if it uses information unavailable at the criticised decision. | MEMORY_GAP | Observed during development |
| OBS-028 | A structurally valid lesson can still encode a strategically incorrect trade-off. | MEMORY_GAP | Observed |
| OBS-029 | Exact-category retrieval is easier to audit than broad fallback retrieval. | EVAL_INFRA | Historical design choice |
| OBS-030 | Empty memory must leave the actor prompt unchanged so Run 1 remains baseline-equivalent. | EVAL_INFRA | Verified |
| OBS-031 | Generated in-combat choices can resemble CARD_REWARD screens; permanent deck-building memory must not be injected by screen name alone. | INTERFACE_GAP | Resolved |
| OBS-032 | Run-level memory can be injected at the shared LLM-call layer instead of rewriting every decision handler. | EVAL_INFRA | Verified |
| OBS-033 | Post-run reflection must complete before the next run starts to prevent stale-memory contamination. | EVAL_INFRA | Resolved |
| OBS-034 | A two-run online smoke confirmed the complete autonomous learning loop. | EVAL_INFRA | Verified |
| OBS-035 | Condition B improved progression but still produced 0 wins, suggesting local gains without overcoming the task ceiling. | REASONING_GAP | Observed in B |
| OBS-036 | Condition B increased permanent card-reward skipping from 2.8% to 14.1%. | REASONING_GAP | Observed |
| OBS-037 | At <=40% max HP, Condition B rested at 27/29 campfires. | REASONING_GAP | Observed |
| OBS-038 | Condition B generated repeated variants of similar lessons rather than a clearly consolidated strategy. | MEMORY_GAP | Observed |
| OBS-039 | Newest-first max-3 retrieval creates a rolling recent-guidance window; older valid lessons can stop influencing behaviour. | MEMORY_GAP | Observed |
| OBS-040 | B learned the local Sapphire Key trade-off but never completed all three keys; all B Act-3 runs lacked Emerald. | PLANNING_GAP | Observed |
| OBS-041 | A Condition-B stall exposed a watchdog bug: receiving `ready_for_command=false` must not terminate recovery polling. | EVAL_INFRA | Resolved |
| OBS-042 | No future-memory leakage was detected across the 30-run Condition B dataset. | EVAL_INFRA | Verified |
| OBS-043 | 8,542/9,223 Condition-B actor calls used at least one retrieved memory. | EVAL_INFRA | Observed |
| OBS-044 | C1 completed 30 reviewed runs and retained 73 final human-curated lessons. | EVAL_INFRA | Verified |
| OBS-045 | Human review changed some well-formed lessons because causal strategy was wrong, context missing, guidance vague, or the lesson false. | MEMORY_GAP | Observed in C1 |
| OBS-046 | C1 inherited B's max-3 exact-category retrieval, limiting later influence of even high-quality corrections. | MEMORY_GAP | Observed design limitation |
| OBS-047 | Trajectory-level C2 feedback lets the reviewer correct run-level causal interpretation without manually editing structured lesson fields. | EVAL_INFRA | Verified |
| OBS-048 | Permanent raw memory plus source-coverage validation prevents older lessons from silently disappearing during consolidation. | MEMORY_INFRA | Implemented |
| OBS-049 | C2 smoke v0.1 exposed cross-category loss: card-selectivity guidance under EVENT was not necessarily visible at CARD_REWARD. | MEMORY_GAP | Observed |
| OBS-050 | Playbook v2 adds `applies_to` so provenance category and applicability can differ. | MEMORY_INFRA | Implemented |
| OBS-051 | B2/C2 use the same official seed order and effectively the same gameplay controller, reducing environmental/controller variation. | EVAL_INFRA | Implemented |
| OBS-052 | C2 smoke v0.1 verified the trajectory -> feedback -> memory -> future retrieval loop. | EVAL_INFRA | Verified |
| OBS-053 | C2 smoke v0.2 verified live cross-category retrieval through `applies_to`. | MEMORY_INFRA | Verified |
| OBS-054 | C2 smoke v0.2 preserved temporal isolation: Run 2 retrieved only Run-1 knowledge. | EVAL_INFRA | Verified |
| OBS-055 | C2 smoke v0.2 retained complete source coverage through two runs. | MEMORY_INFRA | Verified |
| OBS-056 | Smoke Bomb can expose a stale command-ready combat snapshot during escape transition. | INTERFACE_GAP | Resolved |
| OBS-057 | Human C2 feedback can change causal emphasis, not merely wording. | MEMORY_GAP | Observed |
| OBS-058 | B2 smoke v0.2 began with empty memory and produced six raw lessons over two runs. | EVAL_INFRA | Verified |
| OBS-059 | B2 smoke v0.2 ended with seven playbook rules and complete source coverage. | MEMORY_INFRA | Verified |
| OBS-060 | B2 live cross-category retrieval occurred in MAP, COMBAT, CARD_REWARD, REST, and EVENT contexts. | MEMORY_INFRA | Verified |
| OBS-061 | The Smoke Bomb transition guard absorbed stale snapshots and reached COMBAT_REWARD without invalid-command error. | INTERFACE_GAP | Verified |
| OBS-062 | B2 v1.1.0 completed 15 runs but was later invalidated by the permanent card-reward skip loop. | EVAL_INFRA | Invalidated |
| OBS-063 | B2 v1.1.0 nevertheless maintained temporal memory isolation. | MEMORY_INFRA | Verified in invalid dataset |
| OBS-064 | B2 v1.1.0 represented 41 raw lessons through 16 playbook rules with complete provenance coverage. | MEMORY_INFRA | Verified in invalid dataset |
| OBS-065 | Autonomous cumulative reflection repeatedly converged on combat survival, card selectivity, HP, events, potions, and boss/key planning. | MEMORY_GAP | Observed |
| OBS-066 | Even the invalid cumulative B2 batch produced no wins or complete key plan, so long-horizon planning remained unresolved. | PLANNING_GAP | Observed |
| OBS-067 | CommunicationMod may keep a skipped permanent card reward visible on the parent reward list. | INTERFACE_GAP | Observed |
| OBS-068 | B2 v1.1.0 produced 92 repeated skips across 19 reward instances in 9 runs. | EVAL_INFRA | Invalidated impact measured |
| OBS-069 | v1.1.1 tracks skipped reward entries per reward flow while preserving later distinct rewards. | INTERFACE_GAP | Resolved |
| OBS-070 | Final B2 v1.1.1 completed 15 matched runs with mean floor 18.73 and no Act-3 reach. | RESULT | Final |
| OBS-071 | B2 v1.1.1 had zero current/future leakage across 2,924 retrievals. | MEMORY_INFRA | Verified |
| OBS-072 | B2 v1.1.1 consolidated 38 raw lessons into 14 rules with complete source coverage. | MEMORY_INFRA | Verified |
| OBS-073 | The final card-skip guard was live-validated, including a two-card-reward skip/advance case. | INTERFACE_GAP | Verified |
| OBS-074 | Correcting the card-skip loop materially changed B2 outcomes and learning trajectory, confirming the invalid batch could not be reused. | EVAL_INFRA | Observed |
| OBS-075 | Letting a second LLM rewrite human feedback adds strategic distortion and weakens attribution to human teaching. | EXPERIMENT_DESIGN | Resolved by redesign |
| OBS-076 | Final C2 stores human-written strategic guidance verbatim. | MEMORY_INFRA | Implemented |
| OBS-077 | C2 separates strategy from indexing metadata: the organizer may infer only title/category/`applies_to`. | EXPERIMENT_DESIGN | Implemented |
| OBS-078 | Authoritative guidance equality is validated between raw memory and actor-facing playbook rule. | MEMORY_INFRA | Implemented |
| OBS-079 | C2 v1.2.0 stored Neow teaching correctly but failed to retrieve it at the next Neow because `GENERAL` was omitted from scope metadata. | MEMORY_GAP | Invalidated v1.2.0 |
| OBS-080 | v1.2.1 adds explicit decision-category mapping plus a deterministic Neow/start-relic `GENERAL` safeguard. | MEMORY_INFRA | Resolved |
| OBS-081 | The dedicated v1.2.1 scope smoke verified Run-1 authoritative Neow teaching was retrieved at Run-2 `NEOW_BLESSING`. | EVAL_INFRA | Verified |
| OBS-082 | Final C2 v1.2.1 completed exactly 15 matched runs and 15 post-run reviews. | RESULT | Final |
| OBS-083 | C2 v1.2.1 preserved zero current/future leakage across 3,705 retrievals. | MEMORY_INFRA | Verified |
| OBS-084 | Final C2 memory contained 25 raw lessons and 17 playbook rules; 10 runs used HUMAN_TEACHING and 5 APPROVE_INITIAL. | MEMORY_INFRA | Verified |
| OBS-085 | C2 reached Act 2+ on 13/15 runs and Act 3 on 2/15, compared with 6/15 and 0/15 for B2. | RESULT | Final |
| OBS-086 | C2 beat B2 on floor in 11/15 matched seeds and on score in 10/15; mean paired gains were +8.60 floors and +106.87 score. | RESULT | Final |
| OBS-087 | Neither B2 nor C2 achieved a win, so the result supports improved progression rather than solved gameplay. | LIMITATION | Final |
| OBS-088 | Continued C2 learning should use fresh training seeds, followed by a frozen held-out evaluation with feedback/memory updates disabled. | EXPERIMENT_DESIGN | Planned |

## Baseline and autonomous-reflection findings — OBS-022 to OBS-043

The baseline established that remaining failures were primarily strategic after controller stabilization. Condition B then demonstrated that post-run memory can change repeated local behaviour: card skipping increased, low-HP campfire recovery became more conservative, and average progression improved.

However, B also exposed weaknesses in self-reflection: credit assignment, hindsight, repeated lesson regeneration, and failure to solve long-horizon key planning. Because 8,542 of 9,223 actor calls used retrieved memory, memory was active enough to plausibly influence behaviour, but this does not prove that every improvement was caused by a specific lesson.

## Human curation and memory-interface limits — OBS-044 to OBS-050

C1 demonstrated that human review can correct strategically wrong or incomplete reflections. The retained C1 bank contained 61 accepted, 11 corrected, and 1 added lesson.

The C1 study also clarified that improving lesson quality is not enough if retrieval itself hides older or cross-category knowledge. This motivated permanent raw memory, cumulative source coverage, and `applies_to`.

## Cumulative-playbook smoke validation — OBS-051 to OBS-061

C2 and B2 smoke tests verified temporal isolation, source coverage, and live cross-category retrieval.

The Smoke Bomb edge case was treated as a controller transition problem rather than a reasoning failure. The bounded guard was applied identically across B2/C2 before final collection.

## Permanent card-reward bug and corrected B2 — OBS-062 to OBS-074

The invalidated B2 v1.1.0 batch is important provenance because it shows why correctness validation must precede interpretation of model performance.

The old controller could override a deliberate Skip decision by reopening the same reward. Since this changed permanent deck construction, downstream outcomes and learned memory were contaminated. The corrected v1.1.1 control was therefore restarted from empty memory.

Final B2 v1.1.1 is the only B2 dataset used in the matched comparison.

## Authoritative human teaching — OBS-075 to OBS-081

The final C2 design intentionally removes the strategic reviser between human feedback and stored guidance.

The human's wording is the source of truth. A model may index it for retrieval but may not rewrite it.

The v1.2.0 Neow failure showed that even metadata-only organization can affect whether correct teaching is available at the right decision. v1.2.1 therefore adds a narrow deterministic scope safeguard, and the dedicated smoke verified it end-to-end before final collection.

## Final C2 result — OBS-082 to OBS-088

C2 improved descriptive performance substantially relative to B2 under the matched seed sequence:

- mean floor: 27.33 vs 18.73;
- mean score: 251.47 vs 144.60;
- Act 2+: 13/15 vs 6/15;
- Act 3: 2/15 vs 0/15.

The paired direction also favored C2 on most seeds. The strongest interpretation is improved survival depth and long-horizon progression.

The key limitation remains 0 wins for both systems. Therefore the next stage should test whether a more extensively taught C2 agent can generalize to held-out unseen runs after learning is frozen.
