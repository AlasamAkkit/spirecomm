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
| OBS-022 | Final baseline performance is bottlenecked mainly by mid-Act-2 attrition/risk management rather than a recurring controller failure. | REASONING_GAP | Observed in 30-run baseline |
| OBS-023 | Card rewards were skipped infrequently in the baseline, making deck growth/skip discipline a candidate recurring strategic issue. | REASONING_GAP | Observed in 30-run baseline |
| OBS-024 | Low-HP campfire smithing occurred before dangerous Act 2 fights, suggesting resource-preservation decisions are a recurring long-horizon failure mode. | REASONING_GAP | Observed in baseline |
| OBS-025 | Offline self-reflection can produce useful reusable lessons, but can also generate plausible-but-overgeneralized or factually wrong lessons. | MEMORY_GAP | Verified during reflection-v0.2 validation |
| OBS-026 | Reflection quality is affected by credit assignment: the reflector can overfocus on the final combat instead of identifying an earlier deck/resource decision that caused the loss. | MEMORY_GAP | Observed |
| OBS-027 | Reflection can exhibit temporal/hindsight leakage by using information that was only available after the decision being criticised. | MEMORY_GAP | Observed |
| OBS-028 | A lesson can be structurally valid and confidently stated while still encoding an incorrect game trade-off, so Condition B must not be silently human-filtered. | MEMORY_GAP | Observed |
| OBS-029 | Exact-category memory retrieval is easier to audit than broad fallback retrieval; unrelated GENERAL memories can distort specialist decisions. | EVAL_INFRA | Resolved in retrieval prototype |
| OBS-030 | Empty memory must leave the actor prompt unchanged, otherwise Run 1 of a learning condition would no longer be baseline-equivalent. | EVAL_INFRA | Resolved + smoke verified |
| OBS-031 | Generated in-combat card choices can appear through a CARD_REWARD-like screen, so permanent deck-building memories must not be injected based on screen name alone. | INTERFACE_GAP | Resolved + smoke verified |
| OBS-032 | Run-level online reflection can be integrated without modifying every decision handler by injecting retrieved lessons at the shared LLM-call layer. | EVAL_INFRA | Verified |
| OBS-033 | Post-run reflection must complete before the next run starts; otherwise a crash/API failure can create stale-memory contamination. | EVAL_INFRA | Resolved with pause/recovery logic |
| OBS-034 | The two-run online smoke test confirmed the full learning loop: Run 1 with empty memory, post-run reflection, memory append/reload, then Run 2 retrieval of only prior-run lessons. | EVAL_INFRA | Verified |

## OBS-020 — Map action representation ambiguity

During early smoke runs, several LLM outputs matched a legal node's `x` coordinate but were invalid as zero-based action indexes. This could silently send the agent down a route different from the intended one.

**Mitigation:** map choices are letter-labelled. If the model returns a unique `x` coordinate anyway, the decoder explicitly recovers that choice and logs how it was decoded.

**Research implication:** apparent gameplay mistakes may originate from action-representation mismatches rather than strategy.

## OBS-021 — Key telemetry mismatch

The installed CommunicationMod build used during development did not expose the documented key object in the same way expected by the controller, even though key acquisition succeeded in-game.

**Mitigation:** the controller tracks key-producing actions and uses effective inferred key state when the wire state is absent.

## OBS-022 to OBS-024 — Baseline strategic bottlenecks

The 30-run baseline established that the most important remaining errors are strategic rather than interface-level. Act 2 was the main attrition bottleneck. Repeated candidate behaviours include:

- taking card rewards very frequently instead of skipping;
- smithing at low HP before dangerous fights;
- spending or failing to preserve resources when survival margin is small;
- struggling to convert a viable Act 1 deck into reliable Act 2 survivability.

These are useful targets for evaluating whether self-reflection changes repeated behaviour across runs.

## OBS-025 to OBS-028 — Limits of autonomous reflection

Offline validation of `reflection-v0.2` intentionally included trajectories the prompt had not been tuned on. The reflector produced several strong lessons, several reasonable but overgeneralized lessons, and at least one clearly wrong lesson.

Observed failure modes include:

- **credit assignment:** identifying the final symptom instead of the earlier cause;
- **abstraction failure:** lessons that are too broad or prescriptive for the evidence;
- **false learning:** storing a confident but incorrect game rule/trade-off;
- **temporal leakage:** justifying an earlier decision using information only known later.

These failures are not manually corrected in Condition B. Their persistence and downstream effect are part of the experiment.

## OBS-029 to OBS-034 — Learning-system experimental controls

The memory system was deliberately kept simple and auditable:

- exact-category retrieval;
- newest matching lessons first;
- maximum three lessons;
- no unrelated `GENERAL` fallback;
- no human semantic filtering in Condition B;
- no prompt change when retrieval is empty.

The online smoke test verified that a completed run is reflected before a later run starts, memory is reloaded within the same process, and recovery logic can detect a completed run whose reflection did not finish.

This supports the intended Condition B sequence:

```text
Run N
  -> RUN_END
  -> reflection-v0.2
  -> append <=3 lessons
  -> reload memory
  -> Run N+1 may retrieve those lessons
```
