# Structured Logging Schema

The controller records machine-readable experiment events in JSONL. The structured event log is the primary source of truth for runtime behavior, controller provenance, memory retrieval, and run completion.

## 1. Main event log

Active continual C2:

```text
spirecomm/run_events_c2.jsonl
```

Each line is one JSON event.

Common top-level provenance fields include:

```text
timestamp
run_id
agent_version
model
experiment_tag
controller_hotfix
continual_controller_version
decision_architecture
intervention_start_run
research_phase
active_ascension
```

Not every historical phase contains every continual field.

## 2. Run lifecycle events

### `RUN_START`

Records the beginning of a gameplay run.

Important fields:

```text
run_id
character
ascension
requested_seed
continual_controller_version
decision_architecture
```

### `RUN_END`

Records the completed gameplay outcome before/independently of post-run learning finalization.

Typical fields include:

```text
completed_run_number
result
act
floor
score
current_hp
max_hp
gold
keys
```

A `RUN_END` does **not** imply that human review and memory update are complete.

### `POST_RUN_REFLECTION_COMPLETE`

Marks completion of the learning/finalization pipeline for a run.

Important fields can include:

```text
completed_run_number
reflected_run_id
trajectory_file
initial_reflection_file
final_reflection_file
human_review_file
review_decision
memory_ids
appended_memory_ids
memory_size_after
playbook_rule_count
playbook_updated_through_run
recovery
```

This is the event to check before a controller-version transition.

## 3. Decision events

### `LLM_CALL`

Records the model-facing decision protocol.

Useful fields:

```text
decision_type
legal_actions
legal_action_count
raw_answer
selected_index
fallback_used
parse_error
reasoning_effort
input_tokens
output_tokens
latency_ms
base_prompt_characters
prompt_characters
memory_category
memory_ids
```

Structured protocols may additionally record parsed JSON payloads, card scores, committed turn sequences, or controller selection modes.

### `ACTION`

Records the action that was actually issued to the game.

Useful fields:

```text
decision_type
decision_source
legal_actions
selected_action
command
status
metadata
```

Use `ACTION`, not only `LLM_CALL`, to determine what command was actually issued.

## 4. Memory events

### `MEMORY_RETRIEVAL`

Records which playbook rules were exposed to the actor for a decision.

Typical fields:

```text
decision_type
memory_category
memory_policy
memory_ids
source_memory_ids
retrieved_memory_categories
authoritative_rule_ids
authoritative_rule_count
memory_count
candidate_memory_count
omitted_memory_count
memory_top_k
memory_file
playbook_file
playbook_updated_through_run
```

During final controlled B2/C2, retrieval supplied every applicable rule.

**Historical Runs 33–34 only** used bounded focused retrieval:

```text
COMBAT top-k = 8
CARD_REWARD top-k = 10
```

Run-34-only memory policy:

```text
focused_authority_applicability_recent_v1
```

## 5. Sticky combat-plan events

Introduced for Run 33 onward.

### `STICKY_COMBAT_PLAN_CREATED`

Records a newly committed within-turn sequence.

Fields can include:

```text
action_sequence
planned_actions
selected_index
selected_action
remaining_plan
reason
fallback_used
parse_error
```

### `STICKY_COMBAT_PLAN_FOLLOWED`

Records deterministic continuation of a previously committed semantic action.

Useful fields:

```text
expected_action
selected_action
remaining_plan
original_reason
```

### `STICKY_COMBAT_PLAN_INVALIDATED`

Records why a stored plan was abandoned instead of followed.

Possible causes include:

- turn/run changed;
- planned action no longer legal;
- combat ended;
- an intentionally state-changing step required replanning.

## 5a. Cumulative retrieval and verified plans (Runs 35+)

Run 35 introduced `all_applicable_rules_no_topk_with_context_pinning_v1`, with `MEMORY_RETRIEVAL` additions including:

```text
memory_top_k: null
candidate_memory_count
memory_count
omitted_memory_count: 0
authoritative_rule_ids
pinned_authoritative_rule_ids
pinned_authoritative_rule_count
state_entities
source_memory_ids
```

The independent verifier logs `COMBAT_PLAN_VERIFICATION_V13` for **new plans** with `proposed_sequence_descriptions`, `displayed_incoming_damage`, `current_block`, `structured_payload`, `verifier_replaced_plan`, `final_action_sequence`, `parse_error` and token/latency metadata. An approval is not a proof of correct damage mathematics.

Run 36 added `BLOCK_PROJECTION_V131` with `prior_projection`, `final_projection`, `displayed_incoming_before_actions` and static risk/limitation fields. The projection only covers known printed Block cards under modeled statuses; if the intent changes or other effects fire the projection is not exact.

## 5b. Stable execution safeguards (Runs 37+)

Controller v1.4 logs:

- `STABLE_STICKY_PLAN_INVALIDATED` — plan cancelled due to room/encounter transition, unsafe end turn or missing encounter identity; audit `reason` and `discarded_actions`.
- `STABLE_QUEUED_END_TURN_DROPPED` — a queued `End turn` is removed, to be reconsidered in a fresh live state.
- `STABLE_END_TURN_GUARD` — known imminent attack plus effective legal Block caused the selected `End turn` to be overridden; inspect `requested_action`, `forced_action`, `known_unblocked_damage_before` and `safety_reason`.

**Evidence hierarchy:** `RUN_START` identifies controller version; `MEMORY_RETRIEVAL` proves prompt inclusion; `LLM_CALL` shows model proposal; verifier/guard events explain mediation; `ACTION` shows the command issued; `RUN_END` records outcome; `POST_RUN_REFLECTION_COMPLETE` confirms learning update. These are distinct observations.

## 6. Card-reward events

The continual v1.2 permanent reward evaluator records structured scoring of every legal permanent reward option, including Skip.

The controller selection mode is:

```text
argmax_scores_skip_on_tie
```

Important audit fields include:

```text
deck_plan
plan_changed
plan_change_reason
scores
selected_index
selected_action
controller_selection_mode
```

Permanent card decisions should be distinguished from temporary/generated card choices that occur while `room_phase=COMBAT`.

## 7. Safety / recovery events

Historical and current controller versions may emit events such as:

- card-reward skip guard;
- Smoke Bomb transition guard;
- watchdog/reconnect recovery;
- parser fallback;
- human hard-constraint application/not-applied events;
- continual progress updates.

These should be retained rather than filtered out of the research log because they explain controller behavior and whether a trajectory required recovery.

## 8. Supporting logs

### `agent_debug_c2.log`

Human-readable debug trace. Useful for quick inspection of plans, model answers, fallbacks, and controller state.

### `sts_messages_c2.log`

Compact state/message record used to reconstruct tactical state around decisions.

### `state_dumps_c2.jsonl`

Exceptional/full state dumps for debugging unusual states.

These support the structured event log but do not replace it as the main experiment record.

## 9. Run-number vs run-ID rule

Use both when available:

- `completed_run_number` identifies the sequential learning run;
- `run_id` / `source_run_id` identifies the concrete timestamped trajectory.

This is especially important when a process is restarted or when post-run reflection is recovered later.

## 10. Provenance rule

Never infer an old run's controller from the current `test_connection.py`. Use the `continual_controller_version` and `decision_architecture` fields recorded in that run's events.

Never edit collected JSONL lines to make later documentation cleaner. Correct interpretation in documentation or append new diagnostic records instead.
