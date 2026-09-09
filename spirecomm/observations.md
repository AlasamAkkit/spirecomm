Slay the Spire LLM Agent — Observation Log

Purpose

This document records the main observations discovered while developing and running the Slay the Spire LLM agent. Each observation separates controller/interface problems from genuine LLM reasoning problems so later experimental results are interpreted correctly.

Categories

CONTROLLER_GAP — the Python controller does not support a valid interaction.

INTERFACE_GAP — the controller misunderstands or incompletely handles CommunicationMod/protocol behaviour.

OBSERVATION_GAP — the LLM is missing information needed for a good decision.

REASONING_GAP — the LLM has sufficient information and legal actions but chooses poorly.

MEMORY_GAP — the correct action depends on previous state/action history.

ACTION_SPACE_GAP — a strategically valid action exists in-game but is not exposed to the LLM.

EFFICIENCY — unnecessary calls, latency, tokens, or system overhead.

EVAL_INFRA — experiment reliability, logging, reproducibility, or failure diagnosis.

Observation Index

ID

Observation

Category

Status

OBS-001

Generic event screens were initially unsupported

CONTROLLER_GAP

Resolved

OBS-002

High-level choices can create secondary card-selection states

CONTROLLER_GAP

Resolved

OBS-003

Rest sites require a separate decision interface

CONTROLLER_GAP

Resolved

OBS-004

Smith requires card selection followed by confirmation

INTERFACE_GAP

Resolved

OBS-005

Completed rest actions still require PROCEED

INTERFACE_GAP

Resolved

OBS-006

Merchant interaction contains multiple screen states

CONTROLLER_GAP

Resolved

OBS-007

Merchant exit caused an infinite re-entry loop

MEMORY_GAP

Resolved

OBS-008

Treasure rooms require a multi-stage sequence

CONTROLLER_GAP

Resolved

OBS-009

Combat cards can create nested HAND_SELECT states

CONTROLLER_GAP

Resolved

OBS-010

Multi-card selections should be handled sequentially

INTERFACE_GAP

Resolved

OBS-011

Strategic and deterministic actions should be separated

EFFICIENCY

Ongoing

OBS-012

Card information supplied to the LLM is incomplete

OBSERVATION_GAP

Open

OBS-013

Boss relic rewards use a separate decision state

CONTROLLER_GAP

Resolved + live verified

OBS-014

Final run context can be lost at termination

CONTROLLER_GAP / EVAL_INFRA

Resolved

OBS-015

Combat originally omitted potion usage

ACTION_SPACE_GAP

Resolved + live verified

OBS-016

Controller coverage can be tested with synthetic states

EVAL_INFRA

Resolved

OBS-017

Full controller coverage supports autonomous runs

EVAL_INFRA

Live verified

OBS-018

Boss relic selection and inter-Act transitions work live

CONTROLLER_GAP

Live verified

OBS-019

Potion use, targeting, discard and replacement work live

ACTION_SPACE_GAP

Live verified

OBS-020

Map action indices were ambiguous with x-coordinates

INTERFACE_GAP

Resolved + live verified

OBS-021

Key acquisition worked but key telemetry was unreliable

OBSERVATION_GAP / EVAL_INFRA

Resolved + live verified

OBS-022

Long unattended runs can deadlock at the protocol layer

INTERFACE_GAP / EVAL_INFRA

Mitigation implemented; live verification pending

OBS-001 — Generic event screens were initially unsupported

Category: CONTROLLER_GAP
Status: Resolved

What happened: The agent handled Neow but stopped at ordinary ? events.

Root cause: Only Neow-specific event logic existed.

Fix: Added a generic EVENT handler that supplies the LLM with event text, HP, gold, deck, relics, potions, Act/floor, boss and legal choices.

Primary observation: Playing Slay the Spire requires much broader interaction coverage than combat alone.

Research implication: Agent performance depends on the completeness of the environment-to-agent interface, not only LLM reasoning.

OBS-002 — High-level choices can create secondary card-selection states

Category: CONTROLLER_GAP
Status: Resolved

What happened: The LLM chose an event option such as removing a card, then became stuck on the resulting GRID screen.

Root cause: The original controller treated the high-level event option as a complete action.

Fix: Added generic GRID handling for removal, transformation, upgrades and other card-selection effects.

Primary observation: Many game actions are hierarchical rather than atomic.

Research implication: The agent must support variable-length action sequences and secondary decisions.

OBS-003 — Rest sites require a separate decision interface

Category: CONTROLLER_GAP
Status: Resolved

What happened: The agent reached a campfire and stopped.

Root cause: REST states were not handled.

Fix: Added REST decisions using HP, deck, relics, potions, Act/floor, boss and legal campfire choices.

Primary observation: Different game screens require different abstractions of the same run state.

Research implication: Task-specific state representations may be preferable to one universal prompt.

OBS-004 — Smith requires card selection followed by confirmation

Category: INTERFACE_GAP
Status: Resolved

What happened: The LLM chose Smith and selected a card, but the upgrade was not applied.

Root cause: The GRID interaction required a further confirmation step.

Fix: Detect confirmation-ready GRID states and execute the required deterministic confirmation.

Primary observation: Strategic decisions and UI/protocol operations are not the same thing.

Research implication: The controller should execute deterministic UI steps while the LLM handles strategic choices.

OBS-005 — Completed rest actions still require PROCEED

Category: INTERFACE_GAP
Status: Resolved

What happened: After completing a campfire action, the agent remained at the rest site.

Root cause: The game exposed a transitional REST state requiring PROCEED.

Fix: Automatically send PROCEED when no strategic campfire choice remains.

Primary observation: Some states require input but contain no meaningful decision.

Research implication: Avoiding unnecessary LLM calls reduces latency and token cost.

OBS-006 — Merchant interaction contains multiple screen states

Category: CONTROLLER_GAP
Status: Resolved

What happened: The agent entered a merchant but initially could not shop correctly.

Root cause: SHOP_ROOM and SHOP_SCREEN represent different stages.

Fix: Added separate logic for entering, buying, removing cards, re-evaluating inventory and leaving.

Primary observation: One room can contain multiple observations and decision states.

Research implication: The controller must operate over interaction sequences rather than room-level decisions only.

OBS-007 — Merchant exit caused an infinite re-entry loop

Category: MEMORY_GAP
Status: Resolved

What happened: After leaving a shop, the agent repeatedly re-entered and exited it.

Root cause: SHOP_ROOM appears both before entry and after leaving, so a stateless controller treated both states identically.

Fix: Track whether the shop on the current (seed, floor) has already been entered.

Primary observation: Identical observations can require different actions depending on recent history.

Research implication: Even a mostly reactive agent requires limited short-term controller memory.

OBS-008 — Treasure rooms require a multi-stage sequence

Category: CONTROLLER_GAP
Status: Resolved

What happened: The agent reached a chest and stopped.

Root cause: CHEST interactions were not covered.

Fix: Added the deterministic open → reward → proceed sequence, while preserving strategic reward trade-offs where applicable.

Primary observation: Many interactions contain mandatory sub-actions that do not require reasoning.

Research implication: Deterministic control should be separated from LLM decision-making.

OBS-009 — Combat cards can create nested HAND_SELECT states

Category: CONTROLLER_GAP
Status: Resolved

What happened: Cards such as Burning Pact created a follow-up card-selection state that was initially unsupported.

Root cause: Early combat logic assumed a card play completed the interaction.

Fix: Added HAND_SELECT handling with resolving-card context, selectable cards and combat state.

Primary observation: Playing a card can create additional decisions.

Research implication: Combat evaluation should include downstream decisions caused by the selected card.

OBS-010 — Multi-card selections should be handled sequentially

Category: INTERFACE_GAP
Status: Resolved

What happened: Some effects require multiple cards to be selected.

Challenge: Card indices and legal choices can change after each selection.

Fix: Select one card, receive the updated state, then select the next until confirmation is possible.

Primary observation: A multi-step interaction can modify its own action space.

Research implication: Re-observing after every sub-action is safer than executing a pre-planned sequence against stale indices.

OBS-011 — Strategic and deterministic actions should be separated

Category: EFFICIENCY
Status: Ongoing

What happened: Many states had only one meaningful action, such as opening a chest, collecting mandatory gold, confirming an upgrade or proceeding after completion.

Current approach: The controller executes deterministic actions directly and calls the LLM only when meaningful alternatives exist.

Primary observation: Not every game interaction benefits from LLM reasoning.

Research implication: A hybrid controller + LLM architecture reduces cost, latency and unnecessary variability.

OBS-012 — Card information supplied to the LLM is incomplete

Category: OBSERVATION_GAP
Status: Open

What happened: Prompts generally include card name, type, cost, upgrade level and rarity, but not always the full card effect.

Current behaviour: The model partly relies on Slay the Spire knowledge learned during pre-training.

Risk: A poor choice may be caused either by weak reasoning or by insufficient state information.

Primary observation: LLM performance cannot be interpreted independently from the observation representation.

Research implication: A future experiment could compare basic card metadata against explicit card-effect descriptions.

OBS-013 — Boss relic rewards use a separate decision state

Category: CONTROLLER_GAP
Status: Resolved + live verified

What happened: The agent cleared an Act boss but initially became stuck at the boss relic chest.

Root cause: Boss relic choices use a separate BOSS_REWARD state rather than a normal chest/reward flow.

Fix: Added a dedicated boss relic decision prompt using deck, relics, potions, HP, gold and run context.

Live verification: Multiple autonomous runs selected boss relics and continued into later Acts.

Primary observation: Similar-looking reward interactions can require fundamentally different strategic treatment.

Research implication: Boss relic choices are useful long-horizon reasoning decisions because they can modify major mechanics for the remainder of the run.

OBS-014 — Final run context can be lost at termination

Category: CONTROLLER_GAP / EVAL_INFRA
Status: Resolved

What happened: GAME_OVER did not always preserve enough information to reconstruct the state immediately before death.

Root cause: The final observation can contain less context than the preceding active/combat state.

Fix: Cache the latest useful run state and combat state and combine them with final outcome information.

Primary observation: Evaluation may require temporal state preservation beyond the terminal observation.

Research implication: Reliable logging is necessary before causes of failure can be analysed correctly.

OBS-015 — Combat originally omitted potion usage

Category: ACTION_SPACE_GAP
Status: Resolved + live verified

What happened: Early combat actions consisted mainly of cards and END TURN; potions were not exposed.

Root cause: The combat action generator did not include potion actions.

Fix: Added targeted and untargeted potion use plus legal potion discard.

Live verification: Potions were successfully used during autonomous runs.

Primary observation: The model can only be evaluated against actions that the controller actually exposes.

Research implication: Missing actions must not be mistaken for LLM reasoning failures.

OBS-016 — Controller coverage can be tested with synthetic states

Category: EVAL_INFRA
Status: Resolved

What happened: Rare states were slow to reach naturally, making live-only testing inefficient.

Fix: Added synthetic CommunicationMod-like states and ran them through the same controller with LLM calls disabled.

Primary observation: Controller correctness and model intelligence are separable problems.

Research implication: Synthetic interface tests help establish controller coverage before strategic evaluation.

OBS-017 — Full controller coverage supports autonomous runs

Category: EVAL_INFRA
Status: Live verified

What happened: After filling the major controller gaps, the agent completed multiple long autonomous runs.

Evidence: v0.2.2 smoke testing produced no UNHANDLED_STATE, no controller ERROR, no true map fallback, and reached as far as Floor 50 / the Act 3 boss.

Primary observation: The bottleneck shifted from "can the agent interact with the game?" toward "how good are its decisions?"

Research implication: This marks the transition from controller development to meaningful baseline LLM evaluation.

OBS-018 — Boss relic selection and inter-Act transitions work live

Category: CONTROLLER_GAP
Status: Live verified

What happened: Boss reward support required real-game confirmation beyond synthetic tests.

Live verification: Runs successfully defeated Act bosses, selected boss relics, transitioned to the next Act and continued playing.

Primary observation: Synthetic tests are useful but important transitions should also be verified in live trajectories.

Research implication: Both synthetic and live validation are needed before freezing an experimental baseline.

OBS-019 — Potion use, targeting, discard and replacement work live

Category: ACTION_SPACE_GAP
Status: Live verified

What happened: Potion support was expanded from collection to actual combat use and inventory management.

Live verification: The agent successfully used targeted and untargeted potions, discarded potions and made room for replacement potions.

Primary observation: Potion handling includes both tactical and resource-management decisions.

Research implication: Baseline analysis should later determine whether potion timing itself is strategically poor even though the interface works correctly.

OBS-020 — Map action indices were ambiguous with x-coordinates

Category: INTERFACE_GAP
Status: Resolved + live verified

What happened: Map actions were originally numbered, while the action descriptions also contained numerical map x-coordinates. The model sometimes returned the desired coordinate rather than the action index.

Impact: The controller could reject the intended choice and fall back to another route.

Fix: Changed map choices to letter labels (A, B, C, …) and added unique x-coordinate recovery.

Live verification: In the v0.2.2 smoke batch, all recorded map choices decoded correctly through the letter scheme with no true fallback.

Primary observation: Representation ambiguity can look like an LLM reasoning failure even when the model's intended route is sensible.

Research implication: Action encodings should avoid overlapping semantically with game-state values.

OBS-021 — Key acquisition worked but key telemetry was unreliable

Category: OBSERVATION_GAP / EVAL_INFRA
Status: Resolved + live verified

What happened: The agent visibly acquired Ruby, Emerald and Sapphire Keys, but logs did not reliably show ownership.

Root cause: Key state was not consistently exposed through the available game telemetry.

Fix: Added controller-side tracked key state and structured KEY_TRACK_UPDATE events, while using authoritative game key state when available.

Live verification: The smoke batch correctly recorded key acquisitions, including runs with all three keys tracked.

Primary observation: Persistent consequences sometimes need to be reconstructed when the external interface provides incomplete telemetry.

Research implication: This controller state must be distinguished from future cross-run learning memory.

OBS-022 — Long unattended runs can deadlock at the protocol layer

Category: INTERFACE_GAP / EVAL_INFRA
Status: Mitigation implemented; live verification pending

What happened: During attempts to collect the 30-run baseline, the agent froze mid-run.

Two patterns were observed:

The same GRID state repeatedly appeared and the agent repeatedly selected the same action without progress.

In another run, an LLM decision completed successfully, but no subsequent useful state arrived and the run stopped progressing.

Important finding: The second freeze occurred without an API exception, timeout, retry or fallback. Therefore an apparent "LLM freeze" can actually be a controller/environment communication deadlock.

Root cause: The system could deadlock when a command failed to advance the interaction, an error state was not handled, no next state arrived, or the controller returned no command while CommunicationMod was waiting.

Mitigation added in baseline v1.0.2:

explicit CommunicationMod error recovery

state watchdog and resynchronisation request

no-command recovery

GRID repeated-state/progress detection

avoidance of repeatedly issuing an ineffective GRID choice when possible

Primary observation: "The LLM stopped playing" does not necessarily mean the LLM failed.

Research implication: Long-duration autonomous experiments require liveness checks, progress detection and protocol recovery in addition to correct decision logic.

Next validation: Run the revised controller unattended and confirm that the recovery mechanisms prevent further deadlocks before treating this issue as fully resolved.

Emerging Themes

1. Environment and interaction coverage

Early failures were dominated by unsupported game states rather than strategic reasoning.

Relevant observations: OBS-001, 003, 006, 008, 013, 015.

2. Hierarchical and multi-stage actions

Many game actions create follow-up states instead of completing immediately.

Relevant observations: OBS-002, 004, 005, 009, 010.

3. Short-term controller memory and temporal context

Some interactions cannot be solved from the current observation alone.

Relevant observations: OBS-007, 014, 021.

This is different from the future cross-run learning memory.

4. State and action representation

The way information is encoded for the LLM can materially affect apparent performance.

Relevant observations: OBS-012, 020, 021.

5. Strategic reasoning versus deterministic control

The system has evolved into a hybrid architecture:

Python handles deterministic interaction/protocol steps.

The LLM selects among meaningful strategic alternatives.

Relevant observations: OBS-004, 005, 008, 011.

6. Action-space completeness

A model cannot choose an action it was never given.

Relevant observations: OBS-015, 019.

7. Evaluation reliability

Long-running experiments need reliable logging, state preservation, synthetic testing and deadlock recovery.

Relevant observations: OBS-014, 016, 017, 018, 021, 022.

8. Genuine LLM reasoning quality

Once long-duration execution is stable, new observations should increasingly focus on states where:

sufficient information was supplied,

the important legal actions were exposed,

the controller executed the intended choice correctly,

but the strategic choice was still poor.

Likely areas to investigate during the baseline:

route risk management

card reward choices

Rest vs Smith decisions

potion conservation

boss preparation

combat sequencing

deck/relic synergy

repeated mistakes across independent runs

Current Project Position

Stage 1 — Controller/interface discovery

Early runs mainly exposed missing interaction coverage and protocol assumptions.

Stage 2 — Controller and evaluation infrastructure

Major game states were implemented, structured logging was added, and synthetic tests were used to separate controller failures from LLM failures.

Stage 3 — Baseline stability

v0.2.2 demonstrated reliable multi-run autonomous play in smoke testing. Longer unattended baseline attempts then exposed liveness/deadlock problems, producing OBS-022.

Stage 4 — Strategic baseline analysis

Once the v1.0.2 recovery mechanisms are live-verified, the next aim is to collect the fixed baseline dataset and identify genuine strategic failures.

The main question for the baseline is:

Where does the LLM make poor decisions even when the environment interface is functioning correctly, sufficient information is available, and all important legal actions are exposed?

Those findings should determine what the later reflection / cross-run learning system needs to teach the agent.