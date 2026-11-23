"""Run 56+ v1.7.1: post-Run-55 damage sanity and retrieval correction.

CommunicationMod continues to invoke test_connection.py. Run-55 v1.7.0
source and the locally frozen Run-55 evidence remain immutable.
"""
from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile, BadZipFile

import test_connection_c2_run55 as v17
from run56_policy import optimistic_attack_ceiling, select_rules_v171, _power_amount

base = v17.base
VARIANT = "c2-v1.7.1-run56-damage-sanity-decision-memory+a10"
MEMORY_POLICY = "v171-decision-category-anchors+v17-authoritative-pinning"
CHECKPOINT_FILE = (Path(__file__).resolve().parent / "runs" /
                   "_local_checkpoints" / "C2_through_run55_post_v1_7.zip")

# Historical v1.7 source is not edited. Only this process's v1.7 prompt
# function's policy binding is replaced; all archived teaching remains intact.
v17.select_rules = select_rules_v171
v17.v161.VARIANT = VARIANT


def verify_run55_cutover(events_file, playbook_file, review_file, checkpoint):
    """Read-only, fail-closed gate for finalized and frozen Run 55."""
    checkpoint = Path(checkpoint)
    if not checkpoint.is_file():
        raise ValueError("Run-55 write-once checkpoint missing: " + str(checkpoint))
    try:
        with ZipFile(checkpoint) as archive:
            manifest = json.loads(archive.read("CHECKPOINT_MANIFEST.json"))
            frozen_review = json.loads(archive.read(
                "reflection/condition_c2_outputs/run_55_feedback_review.json"))
    except (BadZipFile, KeyError, json.JSONDecodeError, OSError) as exc:
        raise ValueError("Run-55 checkpoint is not a validated archive") from exc

    review = json.loads(Path(review_file).read_text(encoding="utf-8"))
    if (review.get("status") != "FINALIZED"
            or int(review.get("source_run") or 0) != 55
            or review.get("review_decision") not in
            {"HUMAN_TEACHING", "APPROVE_INITIAL"}):
        raise ValueError("Run-55 review must be FINALIZED.")
    if (review["review_decision"] == "HUMAN_TEACHING"
            and not str(review.get("human_feedback") or "").strip()):
        raise ValueError("Run-55 human feedback is empty")
    run_id = review.get("source_run_id")
    if (manifest.get("run") != 55
            or manifest.get("validation", {}).get("source_run_id") != run_id
            or frozen_review.get("status") != "FINALIZED"
            or frozen_review.get("source_run_id") != run_id
            or frozen_review.get("review_decision") != review["review_decision"]):
        raise ValueError("Run-55 checkpoint does not match finalized review")
    if (review["review_decision"] == "HUMAN_TEACHING"
            and frozen_review.get("human_feedback") != review.get("human_feedback")):
        raise ValueError("Run-55 checkpoint does not contain finalized teaching")

    playbook = json.loads(Path(playbook_file).read_text(encoding="utf-8"))
    if int(playbook.get("updated_through_run") or 0) < 55:
        raise ValueError("Run-55 teaching is not in the playbook")
    ended = reflected = False
    with Path(events_file).open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("completed_run_number") != 55:
                continue
            if item.get("event_type") == "RUN_END" and item.get("run_id") == run_id:
                ended = True
            if (item.get("event_type") == "POST_RUN_REFLECTION_COMPLETE"
                    and item.get("reflected_run_id") == run_id):
                reflected = True
    if not (ended and reflected):
        raise ValueError("Run-55 matching end/reflection events not present")
    return playbook


class ContinualC2Run56Agent(v17.ContinualC2Run55Agent):
    def __init__(self, *args, **kwargs):
        verify_run55_cutover(
            base.EVENTS_FILE, base.PLAYBOOK_FILE,
            Path(__file__).resolve().parent.parent / "reflection" /
            "condition_c2_outputs" / "run_55_feedback_review.json",
            CHECKPOINT_FILE,
        )
        super().__init__(*args, **kwargs)
        if self.completed_run_count < 55:
            raise ValueError("v1.7.1 requires 55 completed runs")
        self.log_debug("RUN56_V171_READY: next_run=" +
                       str(self.completed_run_count + 1) +
                       "; Run-55 checkpoint and teaching validated")

    def log_run_event(self, event_type, game_state=None, **details):
        if event_type == "COMBAT_PLAN_VERIFICATION_V13":
            self._v171_last_verifier = dict(details)
        if event_type == "MEMORY_RETRIEVAL":
            details["memory_policy"] = MEMORY_POLICY
            details["run56_intervention_start_run"] = 56
        return super().log_run_event(event_type, game_state, **details)

    def add_memory_to_prompt(self, decision_type, prompt, game_state=None,
                             memory_category=None,
                             output_instruction="Return ONLY the number."):
        if decision_type in {"COMBAT_PLAN_VERIFIER_V13",
                             "COMBAT_STICKY_TURN_PLAN_V12"}:
            state = game_state or {}
            player = ((state.get("combat_state") or {}).get("player") or {})
            strength = _power_amount(player.get("powers") or [], "Strength")
            prompt += (
                "\nRUN56 DAMAGE SANITY: Player Strength is " + str(strength) +
                ". Apply current Strength BEFORE Vulnerable/Weak and other "
                "modifiers. Never certify lethal from printed/base card "
                "damage alone. Ordinary Block expires before the next turn; "
                "Defend on a pure STRONG_DEBUFF turn is not automatically useful."
            )
            if decision_type == "COMBAT_PLAN_VERIFIER_V13":
                proposed = list(getattr(self, "_run43_original_plan", None) or [])
                screen = optimistic_attack_ceiling(state, proposed)
                if screen is not None and screen["claimed_lethal_disproved"]:
                    prompt += (
                        "\nRUN56 NONLETHAL CERTIFICATE: Even an optimistic "
                        "2x upper bound for the proposed ordinary attacks is " +
                        str(screen["optimistic_damage_ceiling"]) +
                        " versus enemy " + str(screen["enemy_hp"]) +
                        " HP, after Strength=" + str(screen["player_strength"]) +
                        ". The proposed line CANNOT be claimed lethal. "
                        "Evaluate real incoming damage and viable alternatives."
                    )
        return super().add_memory_to_prompt(
            decision_type, prompt, game_state=game_state,
            memory_category=memory_category,
            output_instruction=output_instruction,
        )

    def _verify_new_combat_plan(self, game_state, actions, selected):
        original = [selected.get("description")] + [
            row.get("description")
            for row in (getattr(self, "_sticky_combat_remaining", None) or [])
        ]
        self._v171_last_verifier = None
        result = super()._verify_new_combat_plan(game_state, actions, selected)
        event = self._v171_last_verifier or {}
        payload = event.get("structured_payload") or {}
        if not (payload.get("approved") is True
                and payload.get("estimated_hp_loss") == 0):
            return result
        screen = optimistic_attack_ceiling(game_state, original)
        incoming = int(event.get("displayed_incoming_damage") or 0)
        player = ((game_state or {}).get("combat_state") or {}).get("player") or {}
        current_block = int(player.get("block") or 0)
        if (screen is None or not screen["claimed_lethal_disproved"]
                or incoming <= current_block):
            return result

        self.log_run_event(
            "RUN56_UNFOUNDED_LETHAL_FLAGGED", game_state,
            original_plan=original,
            optimistic_damage_ceiling=screen["optimistic_damage_ceiling"],
            enemy_hp=screen["enemy_hp"],
            player_strength=screen["player_strength"],
            displayed_incoming_damage=incoming,
            reason="Verifier claimed zero HP loss but proposed attacks cannot kill",
        )

        # Override only if known legal Defend would change certain fatal
        # incoming damage to survival. Otherwise preserve the existing legal
        # action; this screen cannot determine globally optimal play.
        project_simple_block = v17.v161.run48.run43.a10.stable.v131.project_simple_block
        hp = int(player.get("current_hp") or 0)
        if incoming >= hp + current_block:
            for action in actions:
                description = str(action.get("description") or "")
                if description not in {"Play Defend", "Play Defend+"}:
                    continue
                projected = project_simple_block(player, [description])
                if incoming < hp + projected["known_projected_block"]:
                    self._clear_sticky_with_audit(
                        game_state, "run56_unfounded_lethal_survival_override")
                    self.log_run_event(
                        "RUN56_SURVIVAL_OVERRIDE", game_state,
                        selected_action=description, incoming_damage=incoming,
                        projected_block=projected["known_projected_block"],
                    )
                    return action
        return result


base.STSAgent = ContinualC2Run56Agent


def main():
    v17.main()


if __name__ == "__main__":
    main()
