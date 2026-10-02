"""Shared B2/C2 post-run reflection and cumulative-memory pipeline.

B2: trajectory -> LLM reflection -> cumulative playbook.
C2: trajectory -> LLM reflection -> human review. If the reviewer approves the
    reflection, its lessons are stored unchanged. If the reviewer supplies new
    teaching, that teaching is stored verbatim; an LLM may classify retrieval
    metadata only and may not rewrite the strategic content.

Every final lesson is retained permanently in raw_memory.jsonl. The actor does
not receive only the newest lessons; instead it receives every applicable rule
from a cumulative playbook. The playbook updater is required to preserve source
coverage for every raw-memory lesson, so an older lesson cannot silently vanish.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prepare_reflection import (
    build_compact_trajectory,
    load_jsonl,
    select_run_state_summaries,
)
from condition_c_reflection import (
    REFLECTION_PROMPT,
    get_usage,
    strip_code_fence,
    validate_reflection,
)

MODEL = "gpt-5.6-luna"
REFLECTION_VERSION = "reflection-v0.2"
FOLLOWUP_VERSION = "followup-memory-v1.1"
PLAYBOOK_VERSION = "cumulative-playbook-v2"
FEEDBACK_REVIEW_VERSION = "trajectory-feedback-v2"
C2_TEACHING_POLICY_VERSION = "authoritative-human-teaching-v1"
FEEDBACK_DECISION_HUMAN_TEACHING = "HUMAN_TEACHING"
FEEDBACK_DECISION_APPROVE_INITIAL = "APPROVE_INITIAL"
FEEDBACK_STATUS_PENDING = "PENDING"
FEEDBACK_STATUS_FINALIZED = "FINALIZED"
FEEDBACK_POLL_SECONDS = 2.0

ALLOWED_CATEGORIES = {
    "COMBAT",
    "CARD_REWARD",
    "REST",
    "MAP",
    "SHOP",
    "EVENT",
    "POTION",
    "BOSS_REWARD",
    "GENERAL",
}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, path)


def _load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def find_run(events: list[dict[str, Any]], completed_run_number: int, run_id: str):
    run_end = None
    for event in events:
        if (
            event.get("event_type") == "RUN_END"
            and event.get("completed_run_number") == completed_run_number
            and event.get("run_id") == run_id
        ):
            run_end = event
            break
    if run_end is None:
        raise ValueError(
            f"Could not find RUN_END for completed run {completed_run_number} / {run_id}."
        )

    run_events = [event for event in events if event.get("run_id") == run_id]
    run_events.sort(key=lambda e: str(e.get("timestamp") or ""))
    return run_events, run_end


def _call_reflection_with_schema_repair(
    client,
    base_input: str,
    *,
    label: str,
    max_attempts: int = 3,
):
    """Call the model and retry when the returned reflection violates the schema.

    Reflection output is part of the experiment infrastructure rather than the
    evaluated gameplay policy. A malformed JSON object (for example, a lesson
    with zero evidence points) should therefore be repaired before the next run
    instead of invalidating an otherwise completed gameplay episode.
    """
    prompt = base_input
    raw_attempts = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_latency_ms = 0.0
    last_error = None

    for attempt in range(1, max_attempts + 1):
        started = time.perf_counter()
        response = client.responses.create(model=MODEL, input=prompt)
        total_latency_ms += (time.perf_counter() - started) * 1000
        raw_text = response.output_text
        raw_attempts.append(f"=== ATTEMPT {attempt} ===\n{raw_text}")

        input_tokens, output_tokens = get_usage(response)
        if isinstance(input_tokens, int):
            total_input_tokens += input_tokens
        if isinstance(output_tokens, int):
            total_output_tokens += output_tokens

        try:
            candidate = json.loads(strip_code_fence(raw_text))
            reflection = validate_reflection(candidate)
            return reflection, "\n\n".join(raw_attempts), {
                "input_tokens": total_input_tokens or None,
                "output_tokens": total_output_tokens or None,
                "latency_ms": round(total_latency_ms, 2),
                "attempts": attempt,
            }
        except Exception as exc:
            last_error = exc
            if attempt >= max_attempts:
                break

            # Re-send the full grounding context plus the exact invalid output.
            # This asks only for schema repair; it does not introduce new game
            # information or alter the lesson-generation policy.
            prompt = (
                base_input
                + "\n\n=== PREVIOUS INVALID OUTPUT ===\n"
                + raw_text
                + "\n=== END INVALID OUTPUT ===\n\n"
                + "VALIDATION ERROR:\n"
                + str(exc)
                + "\n\nReturn the complete corrected reflection as JSON only. "
                  "Keep at most 3 lessons. EVERY lesson must include ALL schema "
                  "fields and MUST contain 1 to 3 non-empty evidence_points "
                  "grounded in the supplied trajectory. Do not add markdown or commentary."
            )

    raise ValueError(
        f"{label} failed schema validation after {max_attempts} attempts: {last_error}"
    ) from last_error


def call_initial_reflector(trajectory: str):
    from openai import OpenAI

    client = OpenAI(timeout=90.0, max_retries=2)
    full_input = (
        REFLECTION_PROMPT
        + "\n\nIMPORTANT OUTPUT REQUIREMENT: Every lesson MUST contain "
          "1 to 3 non-empty evidence_points grounded in the trajectory."
        + "\n\n=== TRAJECTORY START ===\n"
        + trajectory
        + "\n=== TRAJECTORY END ==="
    )

    return _call_reflection_with_schema_repair(
        client,
        full_input,
        label="Initial reflector",
    )


HUMAN_REVISER_PROMPT = """
You are revising a Slay the Spire post-run reflection using human trajectory feedback.

You receive:
1. the compact trajectory of a completed run;
2. the LLM's initial post-run reflection;
3. natural-language feedback from a human reviewer who inspected the run.

Produce the FINAL reusable memory for future runs.

Rules:
- Generate AT MOST 3 lessons.
- Incorporate EVERY substantive point in the human feedback. Merge related points
  when needed so they fit within the 3-lesson limit, but do not silently drop an
  actionable human insight just because it concerns a different decision type.
- If one merged lesson spans multiple decision types (for example EVENT plus
  CARD_REWARD), make that cross-decision relevance explicit in its situation,
  lesson, and reasoning so the cumulative playbook can assign it appropriately.
- The human feedback is guidance about what mattered in the trajectory. Do not
  merely copy its wording; convert it into reusable strategic guidance.
- Prefer causal lessons over the final symptom of death.
- A lesson may connect decisions across several floors when the trajectory and
  feedback support that relationship.
- Do not invent events that are not present in the trajectory.
- Use the current run as evidence, but phrase lessons so they can transfer to
  future runs.
- Avoid absolute claims such as "always" unless the evidence truly supports them.
- Keep the same JSON schema as the original reflector.

Allowed categories:
COMBAT, CARD_REWARD, REST, MAP, SHOP, EVENT, POTION, BOSS_REWARD, GENERAL

Return ONLY valid JSON:
{
  "summary": "...",
  "lessons": [
    {
      "category": "...",
      "title": "...",
      "situation": "...",
      "lesson": "...",
      "evidence_points": ["..."],
      "reasoning": "...",
      "confidence": "high|medium|low"
    }
  ]
}
""".strip()


def call_human_guided_reviser(
    trajectory: str,
    initial_reflection: dict[str, Any],
    human_feedback: str,
):
    from openai import OpenAI

    if not human_feedback.strip():
        raise ValueError("C2 human feedback cannot be empty.")

    client = OpenAI(timeout=90.0, max_retries=2)
    full_input = (
        HUMAN_REVISER_PROMPT
        + "\n\nIMPORTANT OUTPUT REQUIREMENT: Every final lesson MUST contain "
          "1 to 3 non-empty evidence_points grounded in the trajectory."
        + "\n\n=== TRAJECTORY START ===\n"
        + trajectory
        + "\n=== TRAJECTORY END ===\n\n"
        + "=== INITIAL REFLECTION ===\n"
        + json.dumps(initial_reflection, indent=2, ensure_ascii=False)
        + "\n=== END INITIAL REFLECTION ===\n\n"
        + "=== HUMAN FEEDBACK ===\n"
        + human_feedback.strip()
        + "\n=== END HUMAN FEEDBACK ==="
    )

    return _call_reflection_with_schema_repair(
        client,
        full_input,
        label="Human-guided reviser",
    )



HUMAN_TEACHING_METADATA_PROMPT = """
You organize authoritative human teaching for retrieval in a Slay the Spire agent.

The HUMAN TEACHING text is the source of truth. You MUST NOT paraphrase,
summarize, correct, soften, expand, or otherwise rewrite its strategic content.

Your only task is to return retrieval metadata:
- title: a short neutral label, maximum 8 words;
- category: one primary category;
- applies_to: every decision category where the teaching may be relevant.

Allowed categories:
COMBAT, CARD_REWARD, REST, MAP, SHOP, EVENT, POTION, BOSS_REWARD, GENERAL

Use GENERAL only when the teaching is genuinely global or cannot be safely
assigned to a narrower set of decision types.

Return JSON only:
{
  "title": "...",
  "category": "EVENT",
  "applies_to": ["EVENT"]
}
""".strip()


def _validate_human_teaching_metadata(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Human-teaching metadata must be a JSON object.")
    title = str(data.get("title") or "").strip()
    category = str(data.get("category") or "").upper().strip()
    applies_to = data.get("applies_to")
    if not title:
        raise ValueError("Human-teaching metadata requires a non-empty title.")
    if category not in ALLOWED_CATEGORIES:
        raise ValueError(f"Invalid human-teaching category: {category}")
    if not isinstance(applies_to, list) or not applies_to:
        raise ValueError("Human-teaching applies_to must be a non-empty list.")
    normalized = [str(x).upper().strip() for x in applies_to]
    if any(x not in ALLOWED_CATEGORIES for x in normalized):
        raise ValueError(f"Invalid human-teaching applies_to: {normalized}")
    if category not in normalized and "GENERAL" not in normalized:
        normalized.insert(0, category)
    return {
        "title": title,
        "category": category,
        "applies_to": list(dict.fromkeys(normalized)),
    }


def classify_human_teaching(human_feedback: str):
    """Infer retrieval metadata without altering the human's strategic text."""
    from openai import OpenAI

    teaching = str(human_feedback or "").strip()
    if not teaching:
        raise ValueError("Human teaching cannot be empty.")

    client = OpenAI(timeout=90.0, max_retries=2)
    base_input = (
        HUMAN_TEACHING_METADATA_PROMPT
        + "\n\n=== AUTHORITATIVE HUMAN TEACHING ===\n"
        + teaching
        + "\n=== END HUMAN TEACHING ==="
    )
    prompt = base_input
    total_input_tokens = 0
    total_output_tokens = 0
    total_latency_ms = 0.0
    raw_attempts: list[str] = []
    last_error: Exception | None = None

    for attempt in range(1, 4):
        started = time.perf_counter()
        response = client.responses.create(model=MODEL, input=prompt)
        total_latency_ms += (time.perf_counter() - started) * 1000
        raw_text = response.output_text
        raw_attempts.append(f"=== ATTEMPT {attempt} ===\n{raw_text}")
        input_tokens, output_tokens = get_usage(response)
        if isinstance(input_tokens, int):
            total_input_tokens += input_tokens
        if isinstance(output_tokens, int):
            total_output_tokens += output_tokens
        try:
            metadata = _validate_human_teaching_metadata(
                json.loads(strip_code_fence(raw_text))
            )
            return metadata, "\n\n".join(raw_attempts), {
                "input_tokens": total_input_tokens or None,
                "output_tokens": total_output_tokens or None,
                "latency_ms": round(total_latency_ms, 2),
                "attempts": attempt,
            }
        except Exception as exc:
            last_error = exc
            prompt = (
                base_input
                + "\n\nPREVIOUS INVALID METADATA:\n"
                + raw_text
                + "\nVALIDATION ERROR:\n"
                + str(exc)
                + "\nReturn corrected metadata JSON only. Do not rewrite the teaching."
            )

    raise ValueError(
        f"Human-teaching metadata classification failed after retries: {last_error}"
    ) from last_error


def build_authoritative_human_reflection(
    human_feedback: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Represent one human teaching as a structured lesson without rewriting it."""
    teaching = str(human_feedback or "").strip()
    metadata = _validate_human_teaching_metadata(metadata)
    lesson = {
        "category": metadata["category"],
        "title": metadata["title"],
        "situation": (
            "Apply this authoritative human teaching when the current decision "
            "falls within its tagged retrieval scope."
        ),
        "lesson": teaching,
        "evidence_points": [
            "Authoritative human teaching supplied after reviewing this completed run."
        ],
        "reasoning": (
            "The human review is the authoritative teaching source for this C2 "
            "run and is intentionally preserved verbatim."
        ),
        "confidence": "high",
        "applies_to": metadata["applies_to"],
        "authoritative": True,
        "human_feedback_verbatim": teaching,
    }
    return {
        "summary": "Authoritative human teaching stored verbatim for future runs.",
        "lessons": [lesson],
    }


def _decision_category(decision_type: str) -> str:
    value = str(decision_type or "").upper()
    if "BOSS_REWARD" in value:
        return "BOSS_REWARD"
    if "CARD_REWARD" in value:
        return "CARD_REWARD"
    if "REST" in value:
        return "REST"
    if "MAP" in value:
        return "MAP"
    if "SHOP" in value:
        return "SHOP"
    if "EVENT" in value:
        return "EVENT"
    if "POTION" in value:
        return "POTION"
    if "COMBAT" in value or "HAND_SELECT" in value:
        return "COMBAT"
    return "GENERAL"


def _hp_ratio(event: dict[str, Any]) -> float | None:
    hp = event.get("current_hp")
    max_hp = event.get("max_hp")
    try:
        if hp is None or max_hp in (None, 0):
            return None
        return float(hp) / float(max_hp)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def build_run_summary(run_end: dict[str, Any]) -> dict[str, Any]:
    enemies = run_end.get("enemies") or []
    enemy_names = [e.get("name") for e in enemies if isinstance(e, dict) and e.get("name")]
    return {
        "result": run_end.get("result"),
        "act": run_end.get("act"),
        "floor": run_end.get("floor"),
        "score": run_end.get("score"),
        "end_reason": run_end.get("end_reason"),
        "current_hp": run_end.get("current_hp"),
        "max_hp": run_end.get("max_hp"),
        "gold": run_end.get("gold"),
        "boss": run_end.get("act_boss"),
        "final_keys": run_end.get("final_keys") or run_end.get("keys"),
        "final_enemies": enemy_names,
        "final_deck_size": len(run_end.get("final_deck") or []),
        "final_relics": run_end.get("final_relics") or [],
    }


def build_strategic_timeline(run_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    allowed_decisions = {
        "NEOW_BLESSING",
        "MAP_DECISION",
        "CARD_REWARD_DECISION",
        "EVENT_DECISION",
        "SHOP_DECISION",
        "REST_DECISION",
        "BOSS_REWARD_DECISION",
        "SAPPHIRE_KEY_DECISION",
        "POTION_REWARD_REPLACEMENT_DECISION",
    }

    for event in run_events:
        if event.get("event_type") != "ACTION":
            continue
        dt = str(event.get("decision_type") or "").upper()
        if dt not in allowed_decisions:
            continue
        # CARD_REWARD screens reached during COMBAT are temporary/generated-card
        # choices rather than permanent deck rewards.
        if dt == "CARD_REWARD_DECISION" and event.get("room_phase") == "COMBAT":
            continue

        legal = event.get("legal_actions") or []
        timeline.append(
            {
                "act": event.get("act"),
                "floor": event.get("floor"),
                "hp": event.get("current_hp"),
                "max_hp": event.get("max_hp"),
                "gold": event.get("gold"),
                "decision_type": dt,
                "category": _decision_category(dt),
                "selected_action": event.get("selected_action") or event.get("command"),
                "alternatives": legal[:12],
                "keys": event.get("keys") or {},
            }
        )
    return timeline


def detect_review_candidates(
    run_events: list[dict[str, Any]],
    run_end: dict[str, Any],
) -> list[dict[str, Any]]:
    """Flag potentially important moments without declaring them mistakes."""
    candidates: list[dict[str, Any]] = []

    def add(kind: str, title: str, event: dict[str, Any] | None, detail: str):
        candidates.append(
            {
                "kind": kind,
                "title": title,
                "act": event.get("act") if event else run_end.get("act"),
                "floor": event.get("floor") if event else run_end.get("floor"),
                "detail": detail,
            }
        )

    # Final encounter is always worth making easy to inspect.
    enemies = run_end.get("enemies") or []
    enemy_text = ", ".join(
        str(e.get("name")) for e in enemies if isinstance(e, dict) and e.get("name")
    ) or "unknown encounter"
    add(
        "FINAL_OUTCOME",
        "Final encounter / run outcome",
        None,
        f"{run_end.get('result')} at Act {run_end.get('act')} Floor {run_end.get('floor')} against {enemy_text}.",
    )

    card_takes = 0
    card_skips = 0
    seen_elite_floors: set[tuple[Any, Any]] = set()

    for event in run_events:
        if event.get("event_type") != "ACTION":
            continue
        dt = str(event.get("decision_type") or "").upper()
        selected = str(event.get("selected_action") or "")
        ratio = _hp_ratio(event)

        if "REST" in dt and ratio is not None and ratio <= 0.40:
            add(
                "LOW_HP_CAMPFIRE",
                "Low-HP campfire decision",
                event,
                f"HP was {event.get('current_hp')}/{event.get('max_hp')}; selected: {selected}.",
            )

        if event.get("room_type") == "MonsterRoomElite" and ratio is not None and ratio <= 0.50:
            key = (event.get("act"), event.get("floor"))
            if key not in seen_elite_floors:
                seen_elite_floors.add(key)
                add(
                    "LOW_HP_ELITE",
                    "Elite encountered at reduced HP",
                    event,
                    f"Entered/played elite floor at {event.get('current_hp')}/{event.get('max_hp')} HP.",
                )

        if "CARD_REWARD" in dt:
            if selected.lower().startswith("skip"):
                card_skips += 1
            elif selected:
                card_takes += 1
                if card_takes >= 5 and card_skips == 0:
                    add(
                        "DECK_GROWTH",
                        "Several card rewards taken without a skip",
                        event,
                        f"At least {card_takes} permanent card rewards had been taken with no recorded skips at this point.",
                    )
                    # One flag is sufficient.
                    card_skips = -999

        if "BOSS_REWARD" in dt:
            add(
                "BOSS_REWARD",
                "Boss relic decision",
                event,
                f"Selected: {selected}.",
            )

        if "EVENT" in dt and re.search(r"\b(lose|loss|hp|damage|max hp)\b", selected, re.I):
            add(
                "HP_EVENT",
                "Event with HP-related consequence",
                event,
                f"Selected: {selected}.",
            )

        if "SHOP" in dt and selected.lower().startswith("buy"):
            match = re.search(r"for\s+(\d+)\s+gold", selected, re.I)
            if match and event.get("gold"):
                price = int(match.group(1))
                try:
                    fraction = price / float(event.get("gold"))
                except (TypeError, ValueError, ZeroDivisionError):
                    fraction = 0
                if fraction >= 0.50:
                    add(
                        "LARGE_SHOP_SPEND",
                        "Large shop purchase",
                        event,
                        f"Selected: {selected} ({fraction:.0%} of gold held before the purchase).",
                    )

    final_keys = run_end.get("final_keys") or run_end.get("keys") or {}
    if run_end.get("act", 0) >= 2:
        missing = [k for k in ("ruby", "emerald", "sapphire") if not final_keys.get(k, False)]
        if missing:
            add(
                "KEY_PLANNING",
                "Uncollected keys late in the run",
                None,
                "Missing at run end: " + ", ".join(missing) + ".",
            )

    # Keep UI focused. Preserve ordering and remove exact duplicate titles/floors.
    unique: list[dict[str, Any]] = []
    seen = set()
    for item in candidates:
        key = (item.get("kind"), item.get("act"), item.get("floor"), item.get("detail"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique[:16]


def build_or_load_feedback_packet(
    *,
    path: Path,
    completed_run_number: int,
    run_id: str,
    run_events: list[dict[str, Any]],
    run_end: dict[str, Any],
    trajectory_path: Path,
    initial_reflection_path: Path,
    initial_reflection: dict[str, Any],
) -> dict[str, Any]:
    if path.exists():
        document = _load_json(path)
        if (
            document.get("source_run") != completed_run_number
            or document.get("source_run_id") != run_id
        ):
            raise ValueError(f"Feedback packet belongs to a different run: {path}")
        return document

    document = {
        "review_version": FEEDBACK_REVIEW_VERSION,
        "status": FEEDBACK_STATUS_PENDING,
        "source_run": completed_run_number,
        "source_run_id": run_id,
        "created_at": utc_now_iso(),
        "trajectory_file": str(trajectory_path),
        "initial_reflection_file": str(initial_reflection_path),
        "run_summary": build_run_summary(run_end),
        "key_events": detect_review_candidates(run_events, run_end),
        "strategic_timeline": build_strategic_timeline(run_events),
        "initial_reflection": initial_reflection,
        "review_decision": None,
        "human_feedback": "",
        "finalized_at": None,
    }
    _atomic_write_json(path, document)
    return document


def wait_for_human_feedback(path: Path, *, completed_run_number: int, run_id: str):
    while True:
        document = _load_json(path)
        if not isinstance(document, dict):
            raise ValueError(f"Invalid feedback packet: {path}")
        if (
            document.get("source_run") != completed_run_number
            or document.get("source_run_id") != run_id
        ):
            raise ValueError("Feedback packet run identity changed while waiting.")
        if document.get("status") == FEEDBACK_STATUS_FINALIZED:
            decision = str(document.get("review_decision") or "").strip().upper()
            feedback = str(document.get("human_feedback") or "").strip()
            if decision not in {
                FEEDBACK_DECISION_HUMAN_TEACHING,
                FEEDBACK_DECISION_APPROVE_INITIAL,
            }:
                raise ValueError(
                    "Finalized C2 feedback packet has an invalid review_decision."
                )
            if decision == FEEDBACK_DECISION_HUMAN_TEACHING and not feedback:
                raise ValueError(
                    "HUMAN_TEACHING feedback packet has empty human_feedback."
                )
            return document
        time.sleep(FEEDBACK_POLL_SECONDS)


def append_feedback_idempotently(
    *,
    feedback_bank_file: Path,
    completed_run_number: int,
    run_id: str,
    human_feedback: str,
    review_decision: str,
    packet_file: Path,
):
    feedback_bank_file.parent.mkdir(parents=True, exist_ok=True)
    feedback_id = f"feedback_run_{completed_run_number:02d}"
    existing = load_jsonl(feedback_bank_file, tolerate_bad_lines=False)
    for row in existing:
        if row.get("id") == feedback_id:
            if row.get("source_run_id") != run_id:
                raise ValueError(f"Feedback ID collision for {feedback_id}.")
            return row, False

    item = {
        "id": feedback_id,
        "source": "human_trajectory_feedback",
        "source_run": completed_run_number,
        "source_run_id": run_id,
        "review_version": FEEDBACK_REVIEW_VERSION,
        "teaching_policy_version": C2_TEACHING_POLICY_VERSION,
        "review_decision": review_decision,
        "human_feedback": human_feedback.strip(),
        "packet_file": str(packet_file),
        "stored_at": utc_now_iso(),
    }
    with feedback_bank_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return item, True


def load_raw_memory(memory_file: Path) -> list[dict[str, Any]]:
    return load_jsonl(Path(memory_file), tolerate_bad_lines=False)


def append_final_lessons_idempotently(
    *,
    reflection: dict[str, Any],
    completed_run_number: int,
    run_id: str,
    memory_file: Path,
    condition: str,
    human_feedback_id: str | None = None,
    source_override: str | None = None,
):
    memory_file = Path(memory_file)
    memory_file.parent.mkdir(parents=True, exist_ok=True)
    existing = load_raw_memory(memory_file)
    by_id = {item.get("id"): item for item in existing}
    appended: list[str] = []
    items: list[dict[str, Any]] = []
    prefix = condition.lower()

    for idx, lesson in enumerate(reflection.get("lessons") or [], start=1):
        memory_id = f"{prefix}_run_{completed_run_number:02d}_{idx:02d}"
        item = {
            "id": memory_id,
            "source": (
                source_override
                or ("human_guided_reflection" if condition == "C2" else "self_reflection")
            ),
            "condition": condition,
            "source_run": completed_run_number,
            "source_run_id": run_id,
            "reflection_version": REFLECTION_VERSION,
            "followup_version": FOLLOWUP_VERSION,
            "model": MODEL,
            "category": lesson["category"],
            "title": lesson["title"],
            "situation": lesson["situation"],
            "lesson": lesson["lesson"],
            "evidence_points": lesson["evidence_points"],
            "reasoning": lesson["reasoning"],
            "confidence": lesson["confidence"],
            "applies_to": lesson.get("applies_to") or [lesson["category"]],
            "authoritative": bool(lesson.get("authoritative", False)),
            "human_feedback_verbatim": lesson.get("human_feedback_verbatim"),
            "human_feedback_id": human_feedback_id,
            "stored_at": utc_now_iso(),
        }
        items.append(item)
        if memory_id in by_id:
            stored = by_id[memory_id]
            if stored.get("source_run_id") != run_id:
                raise ValueError(f"Memory ID collision for {memory_id}.")
            continue
        with memory_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        by_id[memory_id] = item
        appended.append(memory_id)

    return items, appended


def empty_playbook() -> dict[str, Any]:
    return {
        "playbook_version": PLAYBOOK_VERSION,
        "updated_through_run": 0,
        "updated_at": None,
        "categories": {category: [] for category in sorted(ALLOWED_CATEGORIES)},
    }


def load_playbook(playbook_file: Path) -> dict[str, Any]:
    playbook_file = Path(playbook_file)
    if not playbook_file.exists():
        return empty_playbook()
    document = _load_json(playbook_file)
    return validate_playbook(document, required_memory_ids=None)


PLAYBOOK_PROMPT = """
You maintain a cumulative strategic playbook for a Slay the Spire LLM agent.

The playbook is the compressed representation of ALL final lessons learned so far.
You receive the existing playbook plus the newly learned final lessons from one run.

Update the playbook under these rules:
- Preserve every unique strategic idea from the existing playbook.
- Integrate every new lesson.
- Merge true duplicates or near-duplicates into one stronger rule instead of
  accumulating repetitive wording.
- Do NOT delete an older idea just because it is old.
- Every raw lesson ID listed in REQUIRED MEMORY IDS must appear in at least one
  rule's source_memory_ids. When rules are merged, union their source IDs.
- Keep rules concise enough to be useful inside gameplay prompts.
- Store each rule under ONE primary category, but also provide applies_to with
  EVERY decision category where that rule is useful. Cross-category lessons are
  expected. For example, a lesson learned from a Bite EVENT that also says to
  skip redundant cards should apply to both EVENT and CARD_REWARD.
- applies_to must contain one or more of: COMBAT, CARD_REWARD, REST, MAP, SHOP,
  EVENT, POTION, BOSS_REWARD, GENERAL. Use GENERAL only for truly global rules.
- Do not invent game events or lessons that are not supported by the existing
  playbook or new lessons.
- A rule should have a clear situation (when it applies) and guidance (what to do).

Return ONLY valid JSON with this schema:
{
  "categories": {
    "COMBAT": [
      {
        "when": "...",
        "guidance": "...",
        "rationale": "...",
        "confidence": "high|medium|low",
        "applies_to": ["EVENT", "CARD_REWARD"],
        "source_memory_ids": ["..."]
      }
    ],
    "CARD_REWARD": [],
    "REST": [],
    "MAP": [],
    "SHOP": [],
    "EVENT": [],
    "POTION": [],
    "BOSS_REWARD": [],
    "GENERAL": []
  }
}
""".strip()


def validate_playbook(
    document: dict[str, Any],
    required_memory_ids: set[str] | None,
) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ValueError("Playbook must be a JSON object.")
    categories = document.get("categories")
    if not isinstance(categories, dict):
        raise ValueError("Playbook missing categories object.")

    normalized = {
        "playbook_version": PLAYBOOK_VERSION,
        "updated_through_run": int(document.get("updated_through_run") or 0),
        "updated_at": document.get("updated_at"),
        "categories": {category: [] for category in sorted(ALLOWED_CATEGORIES)},
    }
    covered: set[str] = set()

    for category in ALLOWED_CATEGORIES:
        rows = categories.get(category, []) or []
        if not isinstance(rows, list):
            raise ValueError(f"Playbook category {category} must be a list.")
        for idx, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                raise ValueError(f"Playbook rule {category}/{idx} must be an object.")
            when = str(row.get("when") or "").strip()
            guidance = str(row.get("guidance") or "").strip()
            rationale = str(row.get("rationale") or "").strip()
            confidence = str(row.get("confidence") or "medium").lower().strip()
            sources = row.get("source_memory_ids") or []
            # Backward compatibility for v1 playbooks: a rule without applies_to
            # applies to its primary category only. New v2 consolidation is
            # explicitly instructed to add cross-category applicability.
            applies_to = row.get("applies_to")
            if applies_to is None:
                applies_to = [category]
            if not when or not guidance:
                raise ValueError(f"Playbook rule {category}/{idx} missing when/guidance.")
            if confidence not in ALLOWED_CONFIDENCE:
                raise ValueError(f"Invalid confidence in playbook: {confidence}")
            if not isinstance(applies_to, list) or not applies_to:
                raise ValueError(f"Playbook rule {category}/{idx} has invalid applies_to.")
            applies_to = [str(x).upper().strip() for x in applies_to]
            if any(x not in ALLOWED_CATEGORIES for x in applies_to):
                raise ValueError(
                    f"Playbook rule {category}/{idx} has unsupported applies_to: {applies_to}"
                )
            if category not in applies_to and "GENERAL" not in applies_to:
                # Keep the primary category represented so category provenance
                # never becomes detached from the rule.
                applies_to.insert(0, category)
            unique_applies_to = list(dict.fromkeys(applies_to))
            if not isinstance(sources, list) or not all(isinstance(x, str) and x for x in sources):
                raise ValueError(f"Playbook rule {category}/{idx} has invalid source_memory_ids.")
            unique_sources = list(dict.fromkeys(sources))
            authoritative = bool(row.get("authoritative", False))
            verbatim = row.get("human_feedback_verbatim")
            if authoritative:
                verbatim = str(verbatim or "").strip()
                if not verbatim:
                    raise ValueError(
                        f"Authoritative playbook rule {category}/{idx} is missing verbatim teaching."
                    )
                if guidance != verbatim:
                    raise ValueError(
                        f"Authoritative playbook rule {category}/{idx} rewrote human teaching."
                    )
            covered.update(unique_sources)
            normalized["categories"][category].append(
                {
                    "rule_id": f"pb_{category.lower()}_{idx:02d}",
                    "category": category,
                    "applies_to": unique_applies_to,
                    "when": when,
                    "guidance": guidance,
                    "rationale": rationale,
                    "confidence": confidence,
                    "source_memory_ids": unique_sources,
                    "authoritative": authoritative,
                    "human_feedback_verbatim": verbatim if authoritative else None,
                }
            )

    if required_memory_ids is not None:
        missing = sorted(required_memory_ids - covered)
        if missing:
            raise ValueError(
                "Playbook consolidation dropped raw lesson coverage for: " + ", ".join(missing)
            )
    return normalized


def update_playbook(
    *,
    playbook_file: Path,
    raw_memory_file: Path,
    new_memory_items: list[dict[str, Any]],
    completed_run_number: int,
):
    from openai import OpenAI

    raw_items = load_raw_memory(raw_memory_file)
    required_ids = {str(item.get("id")) for item in raw_items if item.get("id")}
    authoritative_items = [
        item
        for item in raw_items
        if item.get("source") == "human_teaching_verbatim"
        or item.get("authoritative") is True
    ]
    authoritative_ids = {
        str(item.get("id"))
        for item in authoritative_items
        if item.get("id")
    }
    ordinary_required_ids = required_ids - authoritative_ids
    existing = load_playbook(playbook_file)

    # Crash-safe idempotence: if this exact run already produced a playbook
    # covering the complete raw bank, reuse it instead of asking the LLM to
    # reconsolidate and potentially produce a different equivalent wording.
    existing_covered = {
        mid
        for rules in existing.get("categories", {}).values()
        for rule in (rules or [])
        for mid in (rule.get("source_memory_ids") or [])
    }
    existing_run = int(existing.get("updated_through_run") or 0)
    if existing_run == completed_run_number and required_ids.issubset(existing_covered):
        return existing, {
            "input_tokens": None,
            "output_tokens": None,
            "latency_ms": None,
            "reused_existing_playbook": True,
        }
    if existing_run > completed_run_number:
        raise ValueError(
            f"Playbook is already updated through future run {existing_run}; "
            f"cannot process run {completed_run_number}."
        )

    payload_existing = {
        "categories": {
            category: [
                {
                    "when": row.get("when"),
                    "guidance": row.get("guidance"),
                    "rationale": row.get("rationale"),
                    "confidence": row.get("confidence"),
                    "applies_to": row.get("applies_to") or [category],
                    "source_memory_ids": row.get("source_memory_ids") or [],
                }
                for row in existing.get("categories", {}).get(category, [])
                if not row.get("authoritative", False)
            ]
            for category in sorted(ALLOWED_CATEGORIES)
        }
    }

    full_input = (
        PLAYBOOK_PROMPT
        + "\n\n=== EXISTING PLAYBOOK ===\n"
        + json.dumps(payload_existing, indent=2, ensure_ascii=False)
        + "\n=== NEW FINAL LESSONS ===\n"
        + json.dumps(new_memory_items, indent=2, ensure_ascii=False)
        + "\n=== REQUIRED MEMORY IDS ===\n"
        + json.dumps(sorted(required_ids), ensure_ascii=False)
    )

    client = OpenAI(timeout=90.0, max_retries=2)
    last_error: Exception | None = None
    usage = {
        "input_tokens": None,
        "output_tokens": None,
        "latency_ms": None,
        "reused_existing_playbook": False,
    }

    for _attempt in range(3):
        started = time.perf_counter()
        response = client.responses.create(model=MODEL, input=full_input)
        usage["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        usage["input_tokens"], usage["output_tokens"] = get_usage(response)
        try:
            candidate = json.loads(strip_code_fence(response.output_text))
            candidate["playbook_version"] = PLAYBOOK_VERSION
            candidate["updated_through_run"] = completed_run_number
            candidate["updated_at"] = utc_now_iso()
            # Ordinary/self-reflection rules may be consolidated by the LLM.
            # Authoritative human teaching is reattached deterministically from
            # raw memory afterwards so the strategic text cannot be rewritten.
            validated = validate_playbook(
                candidate,
                required_memory_ids=ordinary_required_ids,
            )

            for item in authoritative_items:
                category = str(item.get("category") or "GENERAL").upper()
                if category not in ALLOWED_CATEGORIES:
                    category = "GENERAL"
                applies_to = [
                    str(x).upper().strip()
                    for x in (item.get("applies_to") or [category])
                    if str(x).upper().strip() in ALLOWED_CATEGORIES
                ]
                if not applies_to:
                    applies_to = [category]
                if category not in applies_to and "GENERAL" not in applies_to:
                    applies_to.insert(0, category)

                teaching = str(
                    item.get("human_feedback_verbatim")
                    or item.get("lesson")
                    or ""
                ).strip()
                if not teaching:
                    raise ValueError(
                        f"Authoritative human memory {item.get('id')} has no teaching text."
                    )

                validated["categories"][category].append(
                    {
                        "category": category,
                        "applies_to": list(dict.fromkeys(applies_to)),
                        "when": str(item.get("situation") or "").strip()
                        or "When this human teaching is relevant to the current decision.",
                        "guidance": teaching,
                        "rationale": (
                            "Authoritative human teaching preserved verbatim; "
                            "the playbook may index it but may not rewrite it."
                        ),
                        "confidence": "high",
                        "source_memory_ids": [str(item.get("id"))],
                        "authoritative": True,
                        "human_feedback_verbatim": teaching,
                    }
                )

            validated["playbook_version"] = PLAYBOOK_VERSION
            validated["updated_through_run"] = completed_run_number
            validated["updated_at"] = candidate["updated_at"]
            validated = validate_playbook(
                validated,
                required_memory_ids=required_ids,
            )
            validated["playbook_version"] = PLAYBOOK_VERSION
            validated["updated_through_run"] = completed_run_number
            validated["updated_at"] = candidate["updated_at"]
            _atomic_write_json(Path(playbook_file), validated)
            return validated, usage
        except Exception as exc:  # retry on malformed or coverage-dropping output
            last_error = exc
            full_input += (
                "\n\nVALIDATION ERROR FROM PREVIOUS ATTEMPT:\n"
                + str(exc)
                + "\nReturn a corrected complete playbook."
            )

    raise ValueError(f"Playbook consolidation failed after retries: {last_error}")


def process_completed_run(
    *,
    condition: str,
    completed_run_number: int,
    run_id: str,
    events_file: Path,
    states_file: Path,
    memory_file: Path,
    playbook_file: Path,
    output_dir: Path,
    feedback_bank_file: Path | None = None,
):
    condition = condition.upper().strip()
    if condition not in {"B2", "C2"}:
        raise ValueError("condition must be B2 or C2")

    events_file = Path(events_file)
    states_file = Path(states_file)
    memory_file = Path(memory_file)
    playbook_file = Path(playbook_file)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    events = load_jsonl(events_file, tolerate_bad_lines=False)
    run_events, run_end = find_run(events, completed_run_number, run_id)
    all_states = load_jsonl(states_file, tolerate_bad_lines=True)
    run_states = select_run_state_summaries(all_states, run_events)

    raw_events_path = output_dir / f"run_{completed_run_number:02d}_raw.json"
    states_path = output_dir / f"run_{completed_run_number:02d}_states.json"
    trajectory_path = output_dir / f"run_{completed_run_number:02d}_trajectory_v2.txt"
    initial_path = output_dir / f"run_{completed_run_number:02d}_initial_reflection.json"
    initial_raw_path = output_dir / f"run_{completed_run_number:02d}_initial_reflection_raw.txt"
    final_path = output_dir / f"run_{completed_run_number:02d}_final_reflection.json"
    final_raw_path = output_dir / f"run_{completed_run_number:02d}_final_reflection_raw.txt"
    review_path = output_dir / f"run_{completed_run_number:02d}_feedback_review.json"

    raw_events_path.write_text(json.dumps(run_events, indent=2, ensure_ascii=False), encoding="utf-8")
    states_path.write_text(json.dumps(run_states, indent=2, ensure_ascii=False), encoding="utf-8")
    trajectory = build_compact_trajectory(run_events, run_end, run_states)
    trajectory_path.write_text(trajectory, encoding="utf-8")

    initial_usage = {"input_tokens": None, "output_tokens": None, "latency_ms": None}
    if initial_path.exists():
        initial_doc = _load_json(initial_path)
        if initial_doc.get("source_run_id") != run_id:
            raise ValueError(f"Existing initial reflection belongs to different run: {initial_path}")
        initial_reflection = validate_reflection(
            {"summary": initial_doc.get("summary"), "lessons": initial_doc.get("lessons")}
        )
        initial_reused = True
    else:
        initial_reflection, raw_text, initial_usage = call_initial_reflector(trajectory)
        initial_raw_path.write_text(raw_text, encoding="utf-8")
        initial_doc = {
            "reflection_version": REFLECTION_VERSION,
            "source_run": completed_run_number,
            "source_run_id": run_id,
            "model": MODEL,
            "generated_at": utc_now_iso(),
            "summary": initial_reflection["summary"],
            "lessons": initial_reflection["lessons"],
        }
        _atomic_write_json(initial_path, initial_doc)
        initial_reused = False

    human_feedback = None
    human_feedback_id = None
    revised_usage = {"input_tokens": None, "output_tokens": None, "latency_ms": None}

    if condition == "C2":
        if feedback_bank_file is None:
            raise ValueError("C2 requires feedback_bank_file")
        packet = build_or_load_feedback_packet(
            path=review_path,
            completed_run_number=completed_run_number,
            run_id=run_id,
            run_events=run_events,
            run_end=run_end,
            trajectory_path=trajectory_path,
            initial_reflection_path=initial_path,
            initial_reflection=initial_reflection,
        )
        if packet.get("status") != FEEDBACK_STATUS_FINALIZED:
            packet = wait_for_human_feedback(
                review_path,
                completed_run_number=completed_run_number,
                run_id=run_id,
            )
        human_feedback = str(packet.get("human_feedback") or "").strip()
        feedback_item, _ = append_feedback_idempotently(
            feedback_bank_file=Path(feedback_bank_file),
            completed_run_number=completed_run_number,
            run_id=run_id,
            human_feedback=human_feedback,
            packet_file=review_path,
        )
        human_feedback_id = feedback_item["id"]

        if final_path.exists():
            final_doc = _load_json(final_path)
            if final_doc.get("source_run_id") != run_id:
                raise ValueError(f"Existing final reflection belongs to different run: {final_path}")
            final_reflection = validate_reflection(
                {"summary": final_doc.get("summary"), "lessons": final_doc.get("lessons")}
            )
            final_reused = True
        else:
            final_reflection, final_raw, revised_usage = call_human_guided_reviser(
                trajectory, initial_reflection, human_feedback
            )
            final_raw_path.write_text(final_raw, encoding="utf-8")
            final_doc = {
                "reflection_version": REFLECTION_VERSION,
                "followup_version": FOLLOWUP_VERSION,
                "source_run": completed_run_number,
                "source_run_id": run_id,
                "model": MODEL,
                "generated_at": utc_now_iso(),
                "human_feedback_id": human_feedback_id,
                "summary": final_reflection["summary"],
                "lessons": final_reflection["lessons"],
            }
            _atomic_write_json(final_path, final_doc)
            final_reused = False
    else:
        final_reflection = initial_reflection
        final_reused = initial_reused
        if not final_path.exists():
            final_doc = {
                "reflection_version": REFLECTION_VERSION,
                "followup_version": FOLLOWUP_VERSION,
                "source_run": completed_run_number,
                "source_run_id": run_id,
                "model": MODEL,
                "generated_at": utc_now_iso(),
                "summary": final_reflection["summary"],
                "lessons": final_reflection["lessons"],
            }
            _atomic_write_json(final_path, final_doc)

    memory_items, appended_ids = append_final_lessons_idempotently(
        reflection=final_reflection,
        completed_run_number=completed_run_number,
        run_id=run_id,
        memory_file=memory_file,
        condition=condition,
        human_feedback_id=human_feedback_id,
    )

    playbook, playbook_usage = update_playbook(
        playbook_file=playbook_file,
        raw_memory_file=memory_file,
        new_memory_items=memory_items,
        completed_run_number=completed_run_number,
    )

    return {
        "condition": condition,
        "completed_run_number": completed_run_number,
        "run_id": run_id,
        "reflection_version": REFLECTION_VERSION,
        "followup_version": FOLLOWUP_VERSION,
        "model": MODEL,
        "trajectory_file": str(trajectory_path),
        "initial_reflection_file": str(initial_path),
        "final_reflection_file": str(final_path),
        "human_review_file": str(review_path) if condition == "C2" else None,
        "human_feedback": human_feedback,
        "human_feedback_id": human_feedback_id,
        "matched_state_summaries": len(run_states),
        "initial_lesson_count": len(initial_reflection["lessons"]),
        "lesson_count": len(memory_items),
        "memory_ids": [item["id"] for item in memory_items],
        "appended_memory_ids": appended_ids,
        "memory_size_after": len(load_raw_memory(memory_file)),
        "playbook_rule_count": sum(len(v) for v in playbook["categories"].values()),
        "playbook_file": str(playbook_file),
        "initial_reflection_reused": initial_reused,
        "final_reflection_reused": final_reused,
        "initial_input_tokens": initial_usage["input_tokens"],
        "initial_output_tokens": initial_usage["output_tokens"],
        "initial_latency_ms": initial_usage["latency_ms"],
        "reviser_input_tokens": revised_usage["input_tokens"],
        "reviser_output_tokens": revised_usage["output_tokens"],
        "reviser_latency_ms": revised_usage["latency_ms"],
        "playbook_input_tokens": playbook_usage["input_tokens"],
        "playbook_output_tokens": playbook_usage["output_tokens"],
        "playbook_latency_ms": playbook_usage["latency_ms"],
    }


def find_unprocessed_completed_runs(events_file: Path):
    events = load_jsonl(Path(events_file), tolerate_bad_lines=False)
    completed: dict[int, dict[str, Any]] = {}
    reflected: set[int] = set()

    for event in events:
        number = event.get("completed_run_number")
        if event.get("event_type") == "RUN_END" and isinstance(number, int):
            completed[number] = event
        elif event.get("event_type") == "POST_RUN_REFLECTION_COMPLETE" and isinstance(number, int):
            reflected.add(number)

    return [
        {
            "completed_run_number": number,
            "run_id": event.get("run_id"),
        }
        for number, event in sorted(completed.items())
        if number not in reflected
    ]
