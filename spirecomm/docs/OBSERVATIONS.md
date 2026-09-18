# Research Observations

The main rule for this file is to distinguish controller/interface limitations from genuine LLM reasoning failures.

| ID | Observation | Category | Status |
|---|---|---|---|
| OBS-001 | Generic event screens were initially unsupported. | CONTROLLER_GAP | Resolved |
| OBS-002 | High-level decisions can create secondary card-selection screens. | CONTROLLER_GAP | Resolved |
| OBS-003 | Rest sites require a separate decision interface. | CONTROLLER_GAP | Resolved |
| OBS-004 | Smith requires card selection followed by confirmation. | INTERFACE_GAP | Resolved |
| OBS-005 | Completed rest-site actions can still require `PROCEED`. | INTERFACE_GAP | Resolved |
| OBS-006 | Merchant interaction contains multiple screen states. | CONTROLLER_GAP | Resolved |
| OBS-007 | Merchant exit can produce a state-dependent re-entry loop without short-term controller memory. | MEMORY_GAP | Resolved |
| OBS-008 | Treasure rooms require a multi-stage interaction sequence. | CONTROLLER_GAP | Resolved |
| OBS-009 | Combat cards can generate nested HAND_SELECT decisions. | CONTROLLER_GAP | Resolved |
| OBS-010 | Multi-card selections must be handled sequentially across refreshed states. | INTERFACE_GAP | Resolved |
| OBS-011 | Strategic and deterministic actions should be separated to avoid unnecessary LLM calls. | EFFICIENCY | Ongoing |
| OBS-012 | Card information supplied to the LLM does not include complete semantic card-effect descriptions. | OBSERVATION_GAP | Open |
| OBS-013 | Boss relic rewards use a separate `BOSS_REWARD` state. | CONTROLLER_GAP | Resolved + live verified |
| OBS-014 | Terminal states can lose useful final gameplay context; evaluation needs cached state plus GAME_OVER handling. | EVAL_INFRA | Resolved |
| OBS-015 | The early combat action space excluded potion usage, making some apparent combat failures unfair to attribute to the LLM. | ACTION_SPACE_GAP | Resolved + live verified |
| OBS-016 | Environment-interface coverage can be audited separately from gameplay quality. | EVAL_INFRA | Resolved |
| OBS-017 | Full controller coverage operated across repeated autonomous runs with no persistent unhandled-state blocker. | EVAL_INFRA | Observed |
| OBS-018 | Boss relic selection and inter-Act transition work in live gameplay. | INTERFACE_GAP | Verified |
| OBS-019 | Potion use and full-slot potion replacement work in live gameplay. | INTERFACE_GAP | Verified |
| OBS-020 | Numeric map action indexes are ambiguous with map `x` coordinates; the LLM sometimes returned the intended coordinate rather than the requested index. | INTERFACE_GAP | Resolved |
| OBS-021 | The installed CommunicationMod build omitted `game_state.keys`, so key acquisition could succeed in-game while structured telemetry lacked the key state. | OBSERVATION_GAP | Resolved by controller-side tracking |
| OBS-022 | Final baseline performance is bottlenecked mainly by mid-Act-2 attrition/risk management rather than a recurring controller failure. | REASONING_GAP | Observed in Condition A |
| OBS-023 | Card rewards were skipped infrequently in the baseline, making deck growth/skip discipline a candidate recurring strategic issue. | REASONING_GAP | Changed substantially in Condition B |
| OBS-024 | Low-HP campfire smithing occurred before dangerous Act 2 fights, suggesting resource-preservation decisions are a recurring long-horizon failure mode. | REASONING_GAP | Changed substantially in Condition B |
| OBS-025 | Offline self-reflection can produce useful reusable lessons, but can also generate plausible-but-overgeneralized or factually wrong lessons. | MEMORY_GAP | Verified |
| OBS-026 | Reflection quality is affected by credit assignment: the reflector can overfocus on the final combat instead of identifying an earlier deck/resource decision that caused the loss. | MEMORY_GAP | Persisted |
| OBS-027 | Reflection can exhibit temporal/hindsight leakage by using information that was only available after the decision being criticised. | MEMORY_GAP | Observed during development |
| OBS-028 | A lesson can be structurally valid and confidently stated while still encoding an incorrect game trade-off, so Condition B must not be silently human-filtered. | MEMORY_GAP | Observed |
| OBS-029 | Exact-category memory retrieval is easier to audit than broad fallback retrieval. | EVAL_INFRA | Resolved |
| OBS-030 | Empty memory must leave the actor prompt unchanged, otherwise Run 1 of a learning condition would no longer be baseline-equivalent. | EVAL_INFRA | Verified in Condition B |
| OBS-031 | Generated in-combat card choices can appear through a CARD_REWARD-like screen, so permanent deck-building memories must not be injected based on screen name alone. | INTERFACE_GAP | Resolved |
| OBS-032 | Run-level online reflection can be integrated without modifying every decision handler by injecting retrieved lessons at the shared LLM-call layer. | EVAL_INFRA | Verified |
| OBS-033 | Post-run reflection must complete before the next run starts; otherwise a crash/API failure can create stale-memory contamination. | EVAL_INFRA | Resolved |
| OBS-034 | The two-run online smoke test confirmed the full learning loop. | EVAL_INFRA | Verified |
| OBS-035 | Condition B improved mean/median progression but did not produce a win, suggesting self-reflection helps some behaviours without overcoming the task ceiling. | REASONING_GAP | Observed in 30-run Condition B |
| OBS-036 | Condition B increased permanent card-reward skipping from 2.8% to 14.1%. | REASONING_GAP | Observed |
| OBS-037 | At <=40% max HP, Condition B rested at 27/29 campfires, showing a large change from the baseline low-HP smithing pattern. | REASONING_GAP | Observed |
| OBS-038 | Condition B produced repeated variants of similar lessons, indicating limited strategic consolidation rather than monotonic knowledge accumulation. | MEMORY_GAP | Observed |
| OBS-039 | Newest-first max-3 retrieval creates a rolling recent-guidance window; older lessons can stop influencing behaviour even when still valid. | MEMORY_GAP | Observed |
| OBS-040 | Condition B learned the local Sapphire Key trade-off but still ended 0/30 runs with all three keys; all Act 3 runs lacked Emerald. | PLANNING_GAP | Observed |
| OBS-041 | The interrupted Condition B shop run exposed a watchdog bug: a valid `ready_for_command=false` snapshot must not terminate state-recovery polling. | EVAL_INFRA | Resolved |
| OBS-042 | No future-memory leakage was detected across the 30-run Condition B dataset. | EVAL_INFRA | Verified |
| OBS-043 | 92.6% of Condition B actor calls eventually included at least one retrieved memory, making retrieval a dominant part of the learned policy context. | EVAL_INFRA | Observed |

## OBS-022 to OBS-024 — Baseline strategic bottlenecks

The baseline established that the dominant remaining failures were strategic rather than interface-level. Act 2 was the main attrition bottleneck, with repeated patterns involving card accumulation, low-HP smithing, and weak resource preservation.

These observations became concrete behavioural targets for Condition B.

## OBS-025 to OBS-028 — Limits of autonomous reflection

Offline and online reflection showed several failure modes:

- **credit assignment:** identifying the final symptom instead of the earlier cause;
- **abstraction failure:** lessons that are too broad or prescriptive for the evidence;
- **false learning:** storing a confident but incorrect game rule/trade-off;
- **temporal leakage:** justifying an earlier decision using information only known later.

Condition B intentionally preserved these errors instead of manually correcting them.

## OBS-035 to OBS-040 — Condition B behavioural effects and limits

Condition B changed several behaviours in the expected direction:

- permanent card-reward skip rate rose from 2.8% to 14.1%;
- low-HP campfire recovery became much more conservative;
- mean floor and mean score increased;
- Act 3 was reached in 3/30 runs instead of 1/30.

However, the condition still produced 0 wins.

The clearest long-horizon failure was key planning. The agent frequently ended with the Sapphire Key, but never completed all three keys. Each Act 3 run had Ruby + Sapphire but lacked Emerald. This suggests that explicit local lessons can change an immediate choice while still failing to solve a multi-floor planning problem.

The memory bank also accumulated many near-duplicate lessons. Instead of progressively consolidating a strategy, the system often rediscovered another local formulation of the same advice. Since retrieval only uses the newest three matching memories, older valid lessons can disappear from active context.

## OBS-041 — Watchdog readiness deadlock

One physical Condition B run stalled at an Act 2 shop.

Sequence:

```text
command sent
-> no state for 30 s
-> watchdog sends STATE
-> CommunicationMod returns valid state with ready_for_command=false
-> old controller incorrectly ends watchdog cycle
-> handle_state returns no command
-> process waits indefinitely
```

The fix keeps the watchdog active until `ready_for_command=true`.

The interrupted run had no `RUN_END`, generated no reflection, and did not count toward the 30-run dataset.

## OBS-042 to OBS-043 — Condition B memory integrity

Condition B completed with 30 run reflections and 85 lessons.

No retrieved lesson came from the current or a future run. Empty retrieval preserved the base prompt exactly.

Of 9,223 gameplay LLM calls, 8,542 received at least one memory. This means self-generated memory was active during most later decisions and is therefore a plausible mechanism behind the observed behavioural changes, while still not proving causality for any single run.
