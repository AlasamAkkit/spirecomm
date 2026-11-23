# Run 57 interrupted attempt and v1.7.2 reliability cutover

## What happened (2026-11-23)

The active v1.7.1 controller encountered a permanent card reward after
defeating Chosen, **Act 2 Floor 21**, with 50/74 HP and 43 gold.
Options: Twin Strike+, Burning Pact, Thunderclap, Skip.

The model's CARD_REWARD_EVALUATION_V12 response contained an invalid
unquoted numeric word in the scores object:

    "scores": {"0":46, "1":74, "2": fifty, "3":62}

The v1.7.1 evaluator recorded Skip as a fallback index, then the inherited
RUN55_CARD_REWARD_PARSE_PAUSED guard stopped the agent before issuing any
card-selection command. No gameplay Skip was executed. This parse pause
does not create EXPERIMENT_PAUSED_C2.txt because it is not an API failure.

Interrupted run_id: 20261123T073058_946535Z.

The user made a local evidence backup and closed the game. No RUN_END
exists for this attempt. It must not count as completed. The backup is
local-only. Do not overwrite, clear, or commit its logs.

## v1.7.2 scope and protections

The active test_connection.py now imports test_connection_c2_v172.py and
inherits the unchanged Run56 v1.7.1, Run55 v1.7.0 and Run49 v1.6.1 code.

- Keep existing safe trailing-comma JSON recovery.
- Normalize only known unquoted English numeric words directly in the
  scores object. For example, fifty becomes 50. Preserve the model's
  original answer in the audit log, alongside a repair event. Never edit
  the plan narrative, memories or unrelated fields.
- Validate the complete permanent-card response BEFORE the inherited
  scorer or persistent deck-plan writer can act: required plan fields,
  boolean plan_changed, exact action score indices, numeric finite scores
  from 0 to 100, and nonempty explanations.
- On an invalid response, audit the error and raw answer, then retry the
  model up to two more times (three total). No card choice is issued
  during retries. Log RUN57_CARD_REWARD_RESPONSE_RECOVERED on success.
- After exhaustion, emit RUN57_CARD_REWARD_VALIDATION_PAUSED, write a clear
  EXPERIMENT_PAUSED_C2.txt marker, and exit without choosing a card.
  Infrastructure/API errors remain handled by the existing bounded
  transport retry and pause mechanism.
- If a controller reconnects to an already-in-game state without the
  original run ID, fail closed (RUN57_UNATTACHED_LIVE_GAME_PAUSED).
  Do not silently misattribute an unfinished game.
- At a fresh menu start with an unfinished previous RUN_START, log
  RUN57_PREVIOUS_ATTEMPT_INTERRUPTED before beginning a new attempt.
  Do not fabricate RUN_END or modify the old attempt.

This is a targeted reliability fix, not a guarantee that every future
model, API, game, or computer failure is impossible.

## Local activation (after passing CI and merging into master)

The user already backed up and closed the interrupted Run 57 attempt.
From the PROJECT ROOT (the directory containing spirecomm and reflection):

    git status --short
    git fetch origin
    git switch master
    git pull --ff-only origin master
    & .\spirecomm\venv\Scripts\python.exe .\spirecomm\test_c2_v172_preflight.py

If the venv is elsewhere, invoke the same script using the known working
Python interpreter. Stop on Git conflicts. Never use git reset --hard on
local experiment files.

After the offline tests print OK, launch ModTheSpire and CommunicationMod
normally. The controller will start a NEW recorded attempt of the
still-uncompleted Run 57 with its persistent seed, not resume the
interrupted v1.7.1 session.

Expected new controller variant:

    c2-v1.7.2-run57-retry-card-reward-reliability+a10

Run-57 original and restarted attempts must remain distinguishable in
research analysis. Never copy a saved game into a different run ID,
insert a fake RUN_END, edit c2_continual_progress.json or clear
condition_c2_raw_memory.jsonl / condition_c2_playbook.json.
