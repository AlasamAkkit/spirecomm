# Slay the Spire LLM Agent — Observation Log

## Purpose

This document records primary observations discovered while developing and
running the Slay the Spire LLM agent.

The purpose is not only to document software bugs. Each observation should
identify what prevented the agent from progressing, why it occurred, how it
was addressed, and what the issue suggests about the design or limitations
of LLM-based game-playing agents.

These observations will later be grouped into themes and used to support the
analysis, discussion, limitations, and future work of the Final Year Project.


---

# Observation Categories

## CONTROLLER_GAP

The Python controller does not yet support a valid game interaction.

Example:
The agent reaches a chest but no CHEST handler exists.


## INTERFACE_GAP

The controller misunderstands or incompletely implements the interaction
protocol exposed by CommunicationMod.

Example:
Selecting a card for Smith is not sufficient; CommunicationMod subsequently
requires a CONFIRM command.


## OBSERVATION_GAP

The LLM is not provided with enough information to make a well-informed
decision.

Example:
The prompt contains card names but does not contain their actual card effects.


## REASONING_GAP

The LLM receives sufficient information and valid actions but makes a poor
strategic decision.

Example:
Choosing an unnecessarily dangerous path despite having enough information
to recognise the danger.


## MEMORY_GAP

The current observation is insufficient to determine the correct action
without knowledge of what happened previously.

Example:
SHOP_ROOM appears both before entering and after leaving the merchant.


## EFFICIENCY

The agent works, but the design causes unnecessary model calls, latency, or
token consumption.

Example:
Calling the LLM simply to press a deterministic Confirm button.


---

# Observation Index

| ID | Observation | Category | Status |
|---|---|---|---|
| OBS-001 | Generic event screens were initially unsupported | CONTROLLER_GAP | Resolved |
| OBS-002 | High-level decisions can create secondary card-selection screens | CONTROLLER_GAP | Resolved |
| OBS-003 | Rest sites require a separate decision interface | CONTROLLER_GAP | Resolved |
| OBS-004 | Smith requires card selection followed by confirmation | INTERFACE_GAP | Resolved |
| OBS-005 | Completed rest-site actions still require PROCEED | INTERFACE_GAP | Resolved |
| OBS-006 | Merchant interaction contains multiple screen states | CONTROLLER_GAP | Resolved |
| OBS-007 | Merchant exit produced a state-dependent infinite loop | MEMORY_GAP | Resolved |
| OBS-008 | Treasure rooms require a multi-stage interaction sequence | CONTROLLER_GAP | Resolved |
| OBS-009 | Combat cards can generate nested HAND_SELECT decisions | CONTROLLER_GAP | Resolved |
| OBS-010 | Multi-card selections should be handled sequentially | INTERFACE_GAP | Resolved |
| OBS-011 | Strategic and deterministic actions should be separated | EFFICIENCY | Ongoing |
| OBS-012 | Card information supplied to the LLM is currently incomplete | OBSERVATION_GAP | Open |
| OBS-013 | Boss relic rewards use a separate decision state | CONTROLLER_GAP | Resolved |


---

# OBS-001 — Generic event screens were initially unsupported

**Category:** CONTROLLER_GAP  
**Status:** Resolved

## What happened

The agent successfully interacted with Neow but later reached a normal `?`
event and stopped without making a choice.

## Expected behaviour

The agent should read the event description, inspect the available options,
and choose the option that maximises its probability of completing the run.

## Root cause

The controller contained logic specifically for the Neow event but did not
contain a generic handler for other EVENT screens.

## Fix

A generic EVENT handler was implemented.

The LLM now receives:

- event name
- event description
- current HP and maximum HP
- gold
- deck
- relics
- potions
- Act and floor
- Act boss
- currently legal event options

## Primary observation

Slay the Spire exposes many different interaction types outside combat.

A system capable of selecting combat actions is not sufficient to play the
game. The agent requires an intermediary controller capable of translating
different game interfaces into a common decision-making representation.

## Research implication

Agent performance depends not only on the LLM's reasoning ability but also on
the completeness of the environment-to-agent interface.


---

# OBS-002 — High-level decisions can create secondary card-selection screens

**Category:** CONTROLLER_GAP  
**Status:** Resolved

## What happened

The agent successfully chose an event option that required removing a card,
but then became stuck on the subsequent card-selection screen.

## Expected behaviour

After choosing the high-level event action, the agent should decide which card
to remove.

## Root cause

The controller treated the event decision as a complete action.

In reality, the event created another decision state represented by a `GRID`
screen.

## Fix

A generic GRID handler was implemented to recognise operations including:

- card removal
- card transformation
- card upgrades
- other card-selection effects

## Primary observation

Many Slay the Spire actions are hierarchical rather than atomic.

A single high-level decision can produce one or more secondary decisions.

## Research implication

An LLM game-playing architecture must support variable-length action sequences
rather than assuming every decision maps directly to one environment command.


---

# OBS-003 — Rest sites require a separate decision interface

**Category:** CONTROLLER_GAP  
**Status:** Resolved

## What happened

The agent reached a rest site and stopped.

## Expected behaviour

The agent should evaluate legal campfire actions such as:

- Rest
- Smith
- Recall

## Root cause

The REST screen type was not handled by the controller.

## Fix

A REST decision handler was implemented.

The LLM evaluates the decision using the current run state, including HP,
deck, relics, potions, Act, floor, and boss.

## Primary observation

Different game screens require different abstractions of the same underlying
run state.

Combat, routing, events, shops, and campfires each require different subsets
of information to make useful decisions.

## Research implication

Prompt/state representation may need to be task-dependent rather than using a
single universal representation for every game state.


---

# OBS-004 — Smith requires card selection followed by confirmation

**Category:** INTERFACE_GAP  
**Status:** Resolved

## What happened

The LLM correctly selected Smith at a rest site and correctly selected a card
to upgrade, but the game stopped before applying the upgrade.

## Expected behaviour

The selected card should be upgraded and the game should continue.

## Root cause

After the card was selected, CommunicationMod changed the legal commands.

The card-selection state used:

`CHOOSE`

but the following state required:

`CONFIRM`

## Fix

The controller now detects GRID states where confirmation is available and
automatically sends:

`CONFIRM`

## Primary observation

A strategically meaningful decision and the UI actions required to execute
that decision are not necessarily the same thing.

## Research implication

The LLM should be responsible for strategic decisions, while deterministic UI
operations should generally be performed by the controller.


---

# OBS-005 — Completed rest-site actions still require PROCEED

**Category:** INTERFACE_GAP  
**Status:** Resolved

## What happened

After successfully upgrading a card, the agent remained at the rest site.

## Expected behaviour

The agent should leave the campfire and return to the map.

## Root cause

After completing the campfire action, the REST screen remained active but no
strategic choices remained.

CommunicationMod exposed only a `PROCEED` action.

## Fix

The controller now recognises completed REST states and automatically sends:

`PROCEED`

## Primary observation

The game contains transitional states which require an input despite containing
no meaningful strategic decision.

## Research implication

Sending every state to the LLM would introduce unnecessary latency and cost.

Deterministic state transitions should be handled outside the LLM.


---

# OBS-006 — Merchant interaction contains multiple screen states

**Category:** CONTROLLER_GAP  
**Status:** Resolved

## What happened

The agent reached the merchant room and entered it successfully, but did not
purchase anything.

## Root cause

The merchant interaction contains at least two distinct states:

`SHOP_ROOM`

and

`SHOP_SCREEN`

The first represents entering the merchant while the second contains the
actual purchasable inventory.

## Fix

Separate handlers were implemented for:

- entering the merchant
- evaluating merchant inventory
- purchasing cards
- purchasing relics
- purchasing potions
- purchasing card removal
- leaving the merchant

The shop is re-evaluated after every purchase.

## Primary observation

A location in the game is not necessarily equivalent to one observation or
one decision.

## Research implication

The agent must operate over interaction sequences rather than treating rooms as
single decision points.


---

# OBS-007 — Merchant exit produced a state-dependent infinite loop

**Category:** MEMORY_GAP  
**Status:** Resolved

## What happened

After leaving a merchant, the agent repeatedly entered and exited the same
merchant.

The behaviour became:

SHOP_ROOM  
→ SHOP_SCREEN  
→ leave  
→ SHOP_ROOM  
→ SHOP_SCREEN  
→ leave  
→ ...

## Root cause

`SHOP_ROOM` occurs both:

1. before the merchant has been entered, and
2. after the player leaves the merchant.

A purely reactive controller interpreted both observations identically.

## Fix

The controller records whether the merchant on the current floor has already
been entered.

If it has already been visited, the controller proceeds to the map instead of
entering it again.

## Primary observation

The same observable game state can require different actions depending on
previous actions.

## Research implication

A purely stateless observation-to-action architecture is insufficient for some
Slay the Spire interactions.

Even limited short-term memory can be necessary for correct behaviour.


---

# OBS-008 — Treasure rooms require a multi-stage interaction sequence

**Category:** CONTROLLER_GAP  
**Status:** Resolved

## What happened

The agent reached a treasure chest and stopped.

## Expected behaviour

The agent should:

1. open the chest
2. collect the relic
3. proceed out of the room

## Root cause

The CHEST interaction was not implemented.

## Fix

The controller now handles the deterministic sequence:

`CHOOSE open`

→ collect reward

→ `PROCEED`

## Primary observation

Several game interactions contain mandatory sub-actions that do not require
strategic reasoning.

## Research implication

LLM calls should be reserved for states containing meaningful alternatives.
Otherwise, deterministic controller logic provides lower latency and lower
token cost.


---

# OBS-009 — Combat cards can generate nested HAND_SELECT decisions

**Category:** CONTROLLER_GAP  
**Status:** Resolved

## What happened

The agent played cards such as Burning Pact but became stuck when the card
requested another card from the hand to be selected.

## Expected behaviour

The agent should understand what the currently resolving card does and decide
which card should be discarded, exhausted, or otherwise selected.

## Root cause

Combat logic initially supported only:

- PLAY
- END

It did not support decision states created while resolving a card.

## Fix

A HAND_SELECT handler was implemented.

The LLM receives:

- the card currently being resolved
- selectable cards
- cards already selected
- required number of selections
- hand
- draw pile
- discard pile
- exhaust pile
- enemies
- current combat state

## Primary observation

Choosing which card to play is not always the final decision associated with
that card.

Combat contains nested decisions.

## Research implication

Evaluating an LLM combat agent should include both initial card choice and the
quality of downstream decisions generated by that card.


---

# OBS-010 — Multi-card selections should be handled sequentially

**Category:** INTERFACE_GAP  
**Status:** Resolved

## What happened

Some cards require one card to be selected while others can require two or
more cards.

## Challenge

Selecting several card indices at once is unsafe because the state and
available indices may change after each selection.

## Fix

The controller selects cards sequentially:

HAND_SELECT  
→ choose one card  
→ receive updated state  
→ choose next card  
→ ...  
→ CONFIRM

## Primary observation

Interactive action sequences can modify their own legal action space after
every sub-action.

## Research implication

Re-querying the environment after each sub-action is safer than planning a
complete sequence using stale indices.


---

# OBS-011 — Strategic and deterministic actions should be separated

**Category:** EFFICIENCY  
**Status:** Ongoing

## What happened

During development, several states were discovered where only one sensible
action exists:

- leaving Neow after the decision
- confirming an upgrade
- proceeding after a completed rest site
- opening a treasure chest
- collecting mandatory gold
- collecting a relic
- leaving completed reward screens

## Current approach

The controller executes these actions directly without an LLM call.

The LLM is used only where meaningful alternatives exist.

## Primary observation

Not every game interaction benefits from LLM reasoning.

## Research implication

A hybrid architecture may provide better performance than sending every state
to an LLM.

Potential benefits include:

- lower latency
- reduced token consumption
- fewer invalid actions
- more deterministic behaviour

This should later be quantified using the run logs.


---

# OBS-012 — Card information supplied to the LLM is currently incomplete

**Category:** OBSERVATION_GAP  
**Status:** Open

## What happened

The current prompts generally provide information such as:

- card name
- card type
- cost
- upgrade level
- rarity

However, they do not consistently provide the actual card effect.

For example, the model may see:

`Burning Pact+`

without being explicitly told its exact exhaust and draw behaviour.

## Current behaviour

The LLM relies partly on knowledge of Slay the Spire acquired during
pre-training.

## Risk

This creates uncertainty regarding whether a poor decision is caused by:

1. weak reasoning, or
2. incomplete observation/state representation.

## Primary observation

The quality of an LLM agent cannot be evaluated independently from the
information supplied to it.

## Research implication

A future experiment should compare:

### Condition A
Card names and basic metadata only.

### Condition B
Card names, metadata, and explicit card-effect descriptions.

This would help measure how much agent performance depends on external game
knowledge versus information supplied directly in the observation.


---

# OBS-013 — Boss relic rewards use a separate decision state

**Category:** CONTROLLER_GAP  
**Status:** Resolved

## What happened

The agent successfully defeated the Act 1 boss and collected the normal boss
combat rewards, including gold and the boss card reward.

However, it then became stuck at the boss chest.

## Expected behaviour

The agent should evaluate the three boss relics and select the relic that gives
the highest probability of completing the remaining run.

## Root cause

Boss relic rewards are not represented using the normal CHEST or
COMBAT_REWARD screen types.

After the boss rewards are completed, Slay the Spire transitions into a
TreasureRoomBoss containing a separate:

`BOSS_REWARD`

screen.

The screen exposes the available boss relics through `choice_list` and
`screen_state.relics`.

## Fix

A dedicated BOSS_REWARD decision handler was implemented.

The LLM receives:

- all available boss relics
- current deck
- existing relics
- potions
- HP
- gold
- current Act
- current floor
- boss just defeated

The LLM chooses one boss relic, after which the controller sends the matching
CommunicationMod command.

## Primary observation

Not all relic acquisition decisions are equivalent.

Normal relic rewards usually contain one relic and can therefore be collected
deterministically.

Boss relic rewards contain several mutually exclusive options and represent a
strategically important long-term decision.

## Research implication

The controller must distinguish between interactions that appear conceptually
similar but require fundamentally different reasoning.

This also highlights the importance of long-horizon reasoning. Boss relics can
modify major gameplay mechanics such as:

- energy availability
- card-play restrictions
- enemy intent visibility
- future elite rewards
- deck consistency

A locally attractive relic may therefore be harmful when evaluated against
the current deck and future Acts.

This decision type may later be useful when evaluating genuine LLM strategic
reasoning rather than controller coverage.

---

# Emerging Themes

The observations currently suggest several recurring challenges:

1. Environment and interaction coverage
2. Hierarchical and multi-stage actions
3. Short-term memory and temporal context
4. State / observation representation
5. Separation of strategic reasoning from deterministic control
6. LLM latency and token efficiency
7. Genuine LLM reasoning quality

These themes should be revisited after the controller can reliably complete
entire runs.