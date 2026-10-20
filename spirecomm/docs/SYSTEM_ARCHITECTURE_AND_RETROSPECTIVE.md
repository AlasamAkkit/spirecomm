# C2 Agent: System Architecture, Failure Analysis and Stabilization

> Scope: development through **Run 36**; stable evaluation begins at **Run 37**.  
> Status: historical/engineering reference. Do not change historical controller code or collected events when documenting later results.  
> Current fixed evaluation controller: `c2-continual-teaching-v1.4.0-stable-feedback-loop`.

## 1. What the project actually studies

This FYP investigates an LLM acting in **Slay the Spire** with persistent *external* memory and self-reflection, comparing autonomous lessons with authoritative human teaching. **No LLM weights are updated.** Learning means accumulated lessons become future decision context and affect behavior.

Separate the three kinds of evidence:

1. **Controlled A/B/C1 and matched B2/C2 experiments**: frozen historical comparisons. B2 self-reflection and C2 human teaching each used 15 matched seeds; C2 progressed farther on average. Neither condition won.
2. **Continual C2 Runs 16–36**: exploratory engineering and human-teaching study. The controller itself changed at documented boundaries, so improvements cannot be attributed solely to feedback.
3. **Fixed-controller C2 Runs 37 onward**: intended longitudinal feedback phase. Keep v1.4.0 constant during the evaluation window; only the accumulated memory, run-specific state and random seeds should evolve. Do not imply a Run-37 result until RUN_END and human-reflection events exist.

## 2. Runtime architecture

```text
Slay the Spire (Ironclad)
      |
      | CommunicationMod / BaseMod / ModTheSpire
      v
Python controller: spirecomm/test_connection.py [local v1.4.0]
      |-- parse current game state
      |-- enumerate legal commands/actions
      |-- restore cumulative playbook and run-level deck plan
      |-- build context-specific LLM prompt
      |-- LLM chooses/plans an action or ordered sequence
      |-- second-pass combat-plan verifier (where applicable)
      |-- state-aware safety guards; verify actual action legality
      |-- issue command to game
      +-- emit structured JSONL events and diagnostic logs
      |
      v
RUN_END -> trajectory and initial self-reflection
      -> feedback web app (APPROVE_INITIAL / HUMAN_TEACHING)
      -> final lesson(s) + metadata (category, applies_to, provenance)
      -> append raw memory + update cumulative playbook
      -> POST_RUN_REFLECTION_COMPLETE
      -> next independently seeded run
```

CommunicationMod supplies observable state; the controller cannot perfectly simulate hidden enemy intents, arbitrary card/relic interactions, or future drawn cards. A deterministic safety guard covers only explicitly modeled cases. It is not proof of perfect strategy.

### Important runtime files

| File | Role |
|---|---|
| `spirecomm/test_connection.py` | **Active local entry point**; locally installed as stable v1.4.0 after activation |
| `spirecomm/test_connection_c2_stable.py` | Versioned immutable stable controller source, intended Run 37+ |
| `spirecomm/test_connection_c2_continual_v1_3_1.py` | Historical Run-36 controller; imports older versions |
| `spirecomm/activate_c2_stable.py` | One-time activation + checkpoint/preflight; **does not launch gameplay** |
| `spirecomm/test_c2_stable_preflight.py` | Ten deterministic regression tests (as of stable activation) |
| `reflection/feedback_app.py` | Local UI for human review at `http://127.0.0.1:8765` |
| `reflection/condition_c2_raw_memory.jsonl` | Persistent source lessons and provenance |
| `reflection/condition_c2_playbook.json` | Actor-facing, structured cumulative rule set |
| `reflection/condition_c2_feedback.jsonl` | Review/teaching records |
| `reflection/condition_c2_outputs/run_XX_*` | Per-run trajectory, initial review packet and final reflection |
| `reflection/c2_active_deck_plan.json` | Run-level deck objectives and weaknesses |
| `spirecomm/run_events_c2.jsonl` | Primary event and controller-version provenance |
| `spirecomm/c2_continual_seed_schedule.json` | Persisted independent run seeds |
| `spirecomm/c2_continual_progress.json` | Derived Ascension progression state |

**Repository vs laptop:** the GitHub copy of `test_connection.py` need not be identical to the user's active local copy. Controller provenance comes from `RUN_START.continual_controller_version`, not file contents or GitHub's default branch.

## 3. Memory, feedback, and decision authority

For C2, every completed run is first summarized and self-reflected. The reviewer chooses:

- `APPROVE_INITIAL`: accept the autonomous lessons.
- `HUMAN_TEACHING`: supply direct strategy. The human wording is kept verbatim in raw memory/actor-facing authoritative guidance. An LLM may generate retrieval metadata but must not rewrite the teaching into different advice.

An authoritative rule can apply to `COMBAT`, `CARD_REWARD`, `SHOP`, `MAP`, `GENERAL`, etc. A rule's *primary category* is not necessarily the only place it applies: the `applies_to` metadata drives eligibility.

Authority order: legal game action constraints first; applicable authoritative human teaching second; fixed expert card priors advisory; autonomous/non-authoritative rules and contextual LLM reasoning thereafter. Specific, current-state teaching may outweigh generic advice; apparent contradictions require contextual interpretation rather than silently deleting old lessons.

**Cumulative integrity:** the controller validates that every raw lesson ID is represented by at least one playbook rule. From v1.3 onward, all rules applicable to the current decision enter the prompt (no top-k truncation), with encounter-specific human teaching additionally pinned when state entities match. This guarantees *availability*, not necessarily obedience.

Run-36 finalized baseline (local preflight validated): **36 reflected runs, 50 raw lessons, 36 playbook rules, 36 feedback rows, playbook updated through 36**.

## 4. The planning layers

**Permanent card rewards:** Run-33+ persistent deck planning tracks offense, defense, scaling, draw/energy, AoE, weak points, acquisition priorities, and redundant cards. The model scores offered cards, including Skip; the controller selects the maximum score, preferring Skip on a tied maximum. Fixed card priors are supporting evidence, not hard bans.

**Combat:** The planner proposes an ordered list of currently legal actions; the controller follows the queued legal remainder rather than blindly replanning after every action. When a changing state invalidates a queued action, it replans. From Run 35, a second LLM pass checks newly created plans; from Run 36, known printed Block card projections account for Frail and Dexterity.

**Stable execution safeguards (Run 37+):** invalidate queued combat plans on encounter/room transitions, refuse to blindly reuse queued `End turn`, re-evaluate actual current attack and effective Block, and log protective overrides. Orichalcum's end-turn effect is explicitly considered when evaluating whether forcing a Defend would actually be worse. This layer is deliberately bounded; it does not prevent every strategically poor play.

## 5. Chronological controller history

| Runs | Logged controller era | Change / rationale |
|---|---|---|
| 1–15 | C2 v1.2.1 **controlled** | Matched human-teaching comparison; frozen |
| 16–28 | `c2-continual-teaching-v1.0` | Open-ended C2, fresh unique seeds, persistent memory, Ascension state |
| 29–32 | `v1.1.1-card-prior-turn-planner` | Expert card priors, explicit reward scores, whole-turn plan proposal; actually replanned after every action |
| 33 | `v1.2.0-persistent-planning` | Run-level deck plan, deterministic reward selection, sticky combat, focused memory |
| 34 | `v1.2.1-applicability-recency-hotfix` | Fix ranking of applicable cross-category lessons inside focused top-k |
| 35 | `v1.3.0-cumulative-policy-verified-planning` | Restore all-applicable cumulative policy, pin context-specific teaching, add second-pass plan verifier |
| 36 | `v1.3.1-block-aware-verifier` | Power-aware known Block projection for Frail/Dexterity with audit events |
| 37+ | `v1.4.0-stable-feedback-loop` | Cross-encounter plan invalidation, end-turn safety checks, regression suite; intended fixed controller |

The full exact `continual_controller_version` values are listed in [CONTROLLER_HISTORY.md](CONTROLLER_HISTORY.md). The developed v1.1.2 human-authority wrapper was **not a distinct played phase**. Do not relabel historical runs based on versions written later.

## 6. Failures, diagnosis, fix, and remaining limitation

| Problem / evidence | Root cause / diagnosis | Intervention | What remains uncertain |
|---|---|---|---|
| Permanent card reward reappeared after Skip (invalid B2 v1.1.0) | Reward-screen controller reopened intentionally skipped reward | v1.1.1 deterministic skip guard; invalidated runs excluded from matched data | New game UI edge cases still require testing |
| Neow/start relic human lesson missing from GENERAL (invalid C2 v1.2.0) | Incomplete `applies_to` metadata | C2 v1.2.1 scope mapping/safeguard; restarted controlled data | Other new category metadata can still be wrong |
| Repeated human advice not executed (through Run 28) | Myopic local decisions without persistent tactical/deck structure | Run 29 priors/reward scoring, Run 33 persistent plans | Reasoning and long-term trade-offs are still fallible |
| Run 32 planned Bash+ then defense, replanned away defense | Earlier turn planner discarded entire sequence after first action | Run 33 sticky within-turn plan | Sticky plans can be suboptimal even when followed |
| Run 33 deck plan identified scaling weakness but still picked local damage | Model scoring/plan adherence inconsistency | Conditioned reward scoring and cumulative targeted teaching | No deterministic optimal deck evaluator |
| Run 33 eligible Run-32 authoritative cross-category lesson omitted | `primary category` sorting outranked recency within top-k | Run 34 applicability/recency hotfix | Fixed ranking alone did not prevent top-k exclusion of **older** advice |
| Run 34 old Centurion/Mystic Run-13 lesson fell outside combat top-k | Top-k truncation despite complete long-term storage | Run 35 all-applicable retrieval + state-matched pinning | Longer prompts cost tokens; inclusion is not guaranteed compliance |
| Run 34–35 avoidable damage despite prior teaching | Tactical calculations and HP priorities not consistently reliable | Run 35 independent verifier; more specific human feedback | Second LLM pass can repeat first-pass mathematical errors |
| Run 35 Collector: predicted 49 Block, actual 36 under Frail | Printed vs *effective* Block confused | Run 36 deterministic Frail/Dex card-reference projection | Static projection cannot model every relic/conditional effect |
| Run 36 first Louse fight plan leaked `End turn` to a later fight | Same run ID + turn number and legal description did not uniquely identify encounter | Stable v1.4 invalidates on room/encounter transitions; drops/rechecks queued end-turn | Unknown or unusual transitions still deserve audit |
| Run 36 Spheric Guardian caused major HP loss; scaling stayed unused | Poor long-horizon tactical trade-offs, not simply incorrect Block formula | Human teaching on timely scaling, damage, route risk and potion survival; fixed high-level reminders | No claim all damage was avoidable; fixed-controller feedback should be evaluated over many runs |
| At low HP, shop purchases favored long-term upgrades over immediate protection | Local score priorities underestimated near-term death risk | Survival reminder + user teaching; no absolute card/potion ban | A different purchase is not guaranteed to save a run |
| Many small version changes obscured the effect of teaching | Confounding from both code changes and growing memory | Frozen v1.4.0 boundary for Run 37+ and 10-test preflight | Still observational across independent random seeds |

**Important correction:** the initial Run-35 narrative sometimes recommended merely playing Impervious earlier. Impervious *was* used; the concrete falsifiable arithmetic bug was ignoring Frail. Separating execution bugs from mistaken strategic feedback is essential.

## 7. Verified run outcomes at latest checkpoint

| Run | Outcome | Act/floor | Score | Controller | Notes |
|---|---|---|---:|---|---|
| 33 | LOSS | Act 2, Floor 33 | 292 | v1.2.0 | Persistent planning intervention |
| 34 | LOSS | Act 2, Floor 22 | 194 | v1.2.1 | Top-k still excluded older encounter-specific teaching |
| 35 | LOSS | Act 2, Floor 33 | 273 | v1.3.0 | Full retrieval and verifier active; Frail block error |
| 36 | LOSS | Act 2, Floor 23 | 193 | v1.3.1 | Known Block projection active; cross-encounter plan leak observed |
| 37 | **IN PROGRESS when documented** | — | — | v1.4.0 | Stable phase begins; no result asserted |

Source of truth: local structured `run_events_c2.jsonl`, plus verified archives through Run 35 and local Run-36 preflight. The Run-36 stable snapshot was created locally by activation; it should be committed separately when safe. Cross-run result comparisons here are descriptive because seeds and architectures differ.

## 8. Evaluation method after controller freeze

- **Freeze the implementation** (v1.4.0) over an explicit window, initially proposed Runs 37–50.
- Keep human feedback mandatory between runs. Do not edit source code after routine poor gameplay.
- Store per-run seed, architecture version, run outcome, score/floor, raw lesson additions, retrieved rule coverage, verifier/replacement activity, prevented end-turn overrides, token usage and failures.
- Audit case studies showing a specific human lesson available, then **actually applied**, then associated with an improved choice. A retrieval trace alone proves memory inclusion, not compliance.
- For causal claims, prefer matched seeds and stable configuration or controlled ablations; differing-seed, continuously taught results are exploratory.
- Log any required bug fix as a new engineering intervention with its own boundary, never silently rewrite the old version.

## 9. One-time boundary and normal operation

At Run-36 completion/finalization the local activation command was confirmed to pass: 10/10 tests, 50 raw lessons, 36 rules, compressed checkpoint and installed `test_connection.py`. The user subsequently reported Run 37 playing. Do not run the activation script again or replace the active controller mid-run.

Routine flow: run -> trajectory -> initial reflection -> human web review -> final reflection and playbook update -> next run. See [C2_STABLE_FEEDBACK_WORKFLOW.md](C2_STABLE_FEEDBACK_WORKFLOW.md) and [HUMAN_FEEDBACK_MECHANISM.md](HUMAN_FEEDBACK_MECHANISM.md).

## 10. Research takeaway

The initial bottleneck was not lack of feedback text alone. It included **retrieval eligibility**, **rule omission**, **failure to obey a coherent plan**, **unsafe action execution**, **incorrect game arithmetic**, and **misplaced long-horizon priorities**. Versioned code fixes address executor/retrieval integrity; feedback addresses strategy. The fixed Run-37+ phase is designed to make that distinction measurable rather than obscure it.
