"""Condition C post-run reflection + human-curation pipeline.

The LLM reflector is the same frozen reflection-v0.2 used in Condition B.
The only intended learning-policy difference is that its lessons are reviewed by
a human before any lesson is written to the cross-run memory bank.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from prepare_reflection import (
    build_compact_trajectory,
    load_jsonl,
    select_run_state_summaries,
)


MODEL = "gpt-5.6-luna"
REFLECTION_VERSION = "reflection-v0.2"

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

ALLOWED_CONFIDENCE = {
    "low",
    "medium",
    "high",
}

REVIEW_VERSION = "condition-c-human-review-v1"
REVIEW_STATUS_PENDING = "PENDING"
REVIEW_STATUS_FINALIZED = "FINALIZED"
REVIEW_POLL_SECONDS = 2.0
ALLOWED_HUMAN_ACTIONS = {"ACCEPT", "CORRECT", "REJECT", "ADD"}
ALLOWED_REASON_CODES = {
    "ACCEPT",
    "WRONG_CAUSE",
    "MISSED_INSIGHT",
    "TOO_VAGUE",
    "FALSE_LESSON",
    "LONG_HORIZON_PLANNING",
    "OTHER",
}


# IMPORTANT:
# This is the same reflection-v0.2 prompt that was validated offline.
# Do not casually tune it during Condition B, otherwise the learning mechanism
# changes partway through the experiment.
REFLECTION_PROMPT = """
You are the post-run reflector for a Slay the Spire LLM agent.

You will receive a compact trajectory from one completed run.

Your goal is NOT to replay every decision and NOT to produce a walkthrough.
Your goal is to identify the most important reusable lessons that could improve
future runs.

Generate AT MOST 3 reusable lessons.

============================================================
CORE REFLECTION RULES
============================================================

1. Prioritize causal mistakes over the final symptom of failure.
   A run can end in combat even when the important mistake happened several
   floors earlier.
2. Consider both mistakes to correct and good strategies worth repeating.
3. Prefer lessons that transfer to future runs.
4. A useful lesson must be specific enough to change future behavior.
5. Do not invent information that is not present in the trajectory.
6. Respect the DATA LIMITATIONS section.
7. If evidence is weak, incomplete, or ambiguous, lower confidence.
8. Avoid generic advice such as "play better", "manage HP", "build a strong
   deck", or "block more" unless the lesson states WHEN it applies and WHAT
   behavior should change.

============================================================
EVIDENCE VERIFICATION RULES
============================================================

Before returning EACH lesson, verify every factual claim against the trajectory.
For every lesson:
- cite 1 to 3 concrete evidence points from the trajectory;
- explain why those evidence points support the lesson;
- do not use evidence that contradicts the lesson;
- do not state exact quantities unless explicitly supported.

For CARD_REWARD / deck-building lessons:
- verify exact card counts against FINAL BUILD before stating them;
- distinguish upgraded and unupgraded cards correctly;
- do not count temporary/generated combat cards as permanent deck additions;
- do not claim the deck lacked a type of card unless FINAL BUILD supports it;
- if per-decision deck state is unavailable, avoid claiming exactly what the
  deck contained at that moment unless it can be safely reconstructed.

For COMBAT lessons:
- reason sequentially through the states;
- distinguish the state BEFORE an action from the state AFTER that action;
- if claiming that action X should have been played at a particular decision,
  X MUST appear in the legal alternatives at that exact state;
- do not claim a card was ignored simply because it appears in the hand;
  verify that it was legal and enough energy remained at that decision;
- do not claim a card remained playable after another action unless a later
  state explicitly shows it as legal;
- do not infer exact incoming damage from an intent label alone;
- if a combat counterfactual cannot be established from the logged state,
  frame it as a hypothesis and lower confidence.

For MAP lessons:
- baseline logs do not contain complete map topology;
- never infer that x=1, x=2, etc. corresponds to an elite, campfire, event,
  shop, or monster unless the trajectory explicitly says so.

For generated card choices:
- CARD_REWARD decisions marked as occurring during combat are temporary or
  generated choices and are NOT permanent deck additions.

Monster intent:
- an intent value of DEBUG is not strategically meaningful; ignore it.

You may use general Slay the Spire knowledge to interpret named cards, enemies,
relics, and mechanics, but conclusions must still be supported by the recorded
trajectory. Do not fabricate missing state.

============================================================
SELF-CHECK BEFORE OUTPUT
============================================================

For each proposed lesson, silently check:
A. Is every factual statement supported by the trajectory?
B. Did I confuse an earlier state with a later state?
C. If I recommend a combat action, was it legal at that decision?
D. Did I miscount cards or treat a generated card as permanent?
E. Am I blaming the final combat merely because that is where the run ended?
F. Is this lesson reusable in a future run?
G. Would this lesson actually change a future decision?

If any answer is uncertain, revise the lesson or reduce confidence.

Allowed categories:
COMBAT
CARD_REWARD
REST
MAP
SHOP
EVENT
POTION
BOSS_REWARD
GENERAL

Return VALID JSON ONLY. Do not use Markdown or code fences.

Required structure:

{
  "summary": "2-4 sentence diagnosis of the run",
  "lessons": [
    {
      "category": "REST",
      "title": "short descriptive title",
      "situation": "when this lesson should be retrieved in a future run",
      "lesson": "the reusable recommendation",
      "evidence_points": [
        "specific evidence point 1",
        "specific evidence point 2"
      ],
      "reasoning": "brief explanation of why the evidence supports this lesson",
      "confidence": "high"
    }
  ]
}
""".strip()


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def strip_code_fence(text):
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    return text


def validate_reflection(data):
    if not isinstance(data, dict):
        raise ValueError("Reflection must be a JSON object.")

    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("Reflection must contain a non-empty summary.")

    lessons = data.get("lessons")
    if not isinstance(lessons, list):
        raise ValueError("'lessons' must be a JSON list.")

    if len(lessons) > 3:
        raise ValueError(
            f"Reflector returned {len(lessons)} lessons; maximum is 3."
        )

    required_fields = {
        "category",
        "title",
        "situation",
        "lesson",
        "evidence_points",
        "reasoning",
        "confidence",
    }

    for index, lesson in enumerate(lessons, start=1):
        if not isinstance(lesson, dict):
            raise ValueError(f"Lesson {index} must be a JSON object.")

        missing = required_fields - lesson.keys()
        if missing:
            raise ValueError(
                f"Lesson {index} is missing fields: "
                + ", ".join(sorted(missing))
            )

        category = str(lesson["category"]).upper().strip()
        confidence = str(lesson["confidence"]).lower().strip()

        if category not in ALLOWED_CATEGORIES:
            raise ValueError(
                f"Lesson {index} has invalid category: {category}"
            )

        if confidence not in ALLOWED_CONFIDENCE:
            raise ValueError(
                f"Lesson {index} has invalid confidence: {confidence}"
            )

        lesson["category"] = category
        lesson["confidence"] = confidence

        for field in {
            "title",
            "situation",
            "lesson",
            "reasoning",
        }:
            if not isinstance(lesson[field], str) or not lesson[field].strip():
                raise ValueError(
                    f"Lesson {index} field '{field}' must be non-empty."
                )

        evidence_points = lesson["evidence_points"]

        if not isinstance(evidence_points, list):
            raise ValueError(
                f"Lesson {index} evidence_points must be a list."
            )

        if not (1 <= len(evidence_points) <= 3):
            raise ValueError(
                f"Lesson {index} must contain 1 to 3 evidence points."
            )

        for evidence_index, evidence in enumerate(
            evidence_points,
            start=1,
        ):
            if not isinstance(evidence, str) or not evidence.strip():
                raise ValueError(
                    f"Lesson {index} evidence point {evidence_index} "
                    "must be a non-empty string."
                )

    return data


def get_usage(response):
    usage = getattr(response, "usage", None)

    if usage is None:
        return None, None

    return (
        getattr(usage, "input_tokens", None),
        getattr(usage, "output_tokens", None),
    )


def find_run(events, completed_run_number=None, run_id=None):
    run_end = None

    for event in events:
        if event.get("event_type") != "RUN_END":
            continue

        if (
            completed_run_number is not None
            and event.get("completed_run_number") != completed_run_number
        ):
            continue

        if run_id is not None and event.get("run_id") != run_id:
            continue

        run_end = event
        break

    if run_end is None:
        raise ValueError(
            "Could not find the requested completed RUN_END event."
        )

    resolved_run_id = run_end.get("run_id")

    run_events = [
        event
        for event in events
        if event.get("run_id") == resolved_run_id
    ]

    return run_events, run_end


def load_memory_items(memory_file):
    memory_file = Path(memory_file)

    if not memory_file.exists():
        return []

    items = []

    with memory_file.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {memory_file}"
                ) from exc

            if not isinstance(item, dict):
                raise ValueError(
                    f"Memory line {line_number} must be a JSON object."
                )

            items.append(item)

    return items


def _human_metadata_for_final_index(review_document, final_index):
    """Return provenance metadata for one 1-based final lesson index."""
    for item in review_document.get("interventions", []) or []:
        if item.get("final_lesson_index") == final_index:
            return {
                "human_action": item.get("action"),
                "human_reason_code": item.get("reason_code"),
                "human_note": item.get("note", ""),
                "original_lesson_index": item.get("original_lesson_index"),
            }

    for item in review_document.get("added_lessons", []) or []:
        if item.get("final_lesson_index") == final_index:
            return {
                "human_action": "ADD",
                "human_reason_code": item.get("reason_code"),
                "human_note": item.get("note", ""),
                "original_lesson_index": None,
            }

    return {
        "human_action": "UNKNOWN",
        "human_reason_code": "OTHER",
        "human_note": "",
        "original_lesson_index": None,
    }


def append_human_curated_lessons_idempotently(
    review_document,
    *,
    completed_run_number,
    run_id,
    memory_file,
):
    """Append the human-finalized lessons with deterministic IDs/provenance."""
    memory_file = Path(memory_file)
    memory_file.parent.mkdir(parents=True, exist_ok=True)

    final_reflection = validate_reflection(
        {
            "summary": review_document.get("llm_summary") or "Human-reviewed run lessons.",
            "lessons": review_document.get("final_lessons", []),
        }
    )

    existing = load_memory_items(memory_file)
    existing_ids = {
        str(item.get("id"))
        for item in existing
        if item.get("id")
    }

    memory_items = []
    appended_ids = []

    for lesson_number, lesson in enumerate(final_reflection["lessons"], start=1):
        memory_id = f"human_run_{completed_run_number:02d}_{lesson_number:02d}"
        provenance = _human_metadata_for_final_index(review_document, lesson_number)

        item = {
            "id": memory_id,
            "source": "human_curated",
            "source_run": completed_run_number,
            "source_run_id": run_id,
            "reflection_version": REFLECTION_VERSION,
            "review_version": REVIEW_VERSION,
            "model": MODEL,
            "category": lesson["category"],
            "title": lesson["title"],
            "situation": lesson["situation"],
            "lesson": lesson["lesson"],
            "evidence_points": lesson["evidence_points"],
            "reasoning": lesson["reasoning"],
            "confidence": lesson["confidence"],
            "human_action": provenance["human_action"],
            "human_reason_code": provenance["human_reason_code"],
            "human_note": provenance["human_note"],
            "original_lesson_index": provenance["original_lesson_index"],
            "run_level_human_feedback": review_document.get("human_feedback", ""),
        }

        memory_items.append(item)

        if memory_id in existing_ids:
            existing_item = next(
                (stored for stored in existing if stored.get("id") == memory_id),
                None,
            )
            if existing_item is None:
                raise ValueError(f"Memory ID collision for {memory_id}.")
            if existing_item.get("source_run_id") != run_id:
                raise ValueError(
                    f"Memory ID {memory_id} already exists but belongs to "
                    f"source_run_id={existing_item.get('source_run_id')}, "
                    f"not current run_id={run_id}."
                )
            continue

        with memory_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

        existing_ids.add(memory_id)
        appended_ids.append(memory_id)

    return memory_items, appended_ids


def _atomic_write_json(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(document, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(temp, path)


def build_or_load_human_review_packet(
    *,
    review_path,
    completed_run_number,
    run_id,
    reflection,
    trajectory_path,
    reflection_path,
):
    review_path = Path(review_path)

    if review_path.exists():
        document = json.loads(review_path.read_text(encoding="utf-8"))
        if (
            document.get("source_run") != completed_run_number
            or document.get("source_run_id") != run_id
        ):
            raise ValueError(
                f"Existing human-review packet does not belong to this run: {review_path}"
            )
        return document

    document = {
        "review_version": REVIEW_VERSION,
        "status": REVIEW_STATUS_PENDING,
        "source_run": completed_run_number,
        "source_run_id": run_id,
        "reflection_version": REFLECTION_VERSION,
        "model": MODEL,
        "trajectory_file": str(trajectory_path),
        "reflection_file": str(reflection_path),
        "created_at": utc_now_iso(),
        "reviewed_at": None,
        "llm_summary": reflection["summary"],
        "llm_lessons": reflection["lessons"],
        "human_feedback": "",
        "interventions": [],
        "added_lessons": [],
        "final_lessons": [],
        "instructions": (
            "Run reflection/review_condition_c.py in a separate terminal. "
            "The controller will not begin the next episode until this packet "
            "has status FINALIZED. Final memory may contain at most 3 lessons."
        ),
    }
    _atomic_write_json(review_path, document)
    return document


def validate_finalized_review(document, *, completed_run_number, run_id):
    if document.get("status") != REVIEW_STATUS_FINALIZED:
        raise ValueError("Human review is not FINALIZED.")
    if document.get("source_run") != completed_run_number:
        raise ValueError("Human review source_run mismatch.")
    if document.get("source_run_id") != run_id:
        raise ValueError("Human review source_run_id mismatch.")

    interventions = document.get("interventions", []) or []
    added = document.get("added_lessons", []) or []

    for item in interventions:
        action = str(item.get("action", "")).upper()
        reason = str(item.get("reason_code", "")).upper()
        if action not in ALLOWED_HUMAN_ACTIONS - {"ADD"}:
            raise ValueError(f"Invalid human action: {action}")
        if reason not in ALLOWED_REASON_CODES:
            raise ValueError(f"Invalid human reason code: {reason}")

    for item in added:
        reason = str(item.get("reason_code", "")).upper()
        if reason not in ALLOWED_REASON_CODES:
            raise ValueError(f"Invalid added-lesson reason code: {reason}")

    final_reflection = validate_reflection(
        {
            "summary": document.get("llm_summary") or "Human-reviewed run lessons.",
            "lessons": document.get("final_lessons", []),
        }
    )
    if len(final_reflection["lessons"]) > 3:
        raise ValueError("Condition C final memory may contain at most 3 lessons per run.")

    return document


def wait_for_human_review(
    review_path,
    *,
    completed_run_number,
    run_id,
    poll_seconds=REVIEW_POLL_SECONDS,
):
    """Block without using stdin; stdin is reserved for CommunicationMod."""
    review_path = Path(review_path)
    last_mtime = None

    while True:
        try:
            stat = review_path.stat()
            if stat.st_mtime_ns != last_mtime:
                document = json.loads(review_path.read_text(encoding="utf-8"))
                last_mtime = stat.st_mtime_ns
                if document.get("status") == REVIEW_STATUS_FINALIZED:
                    return validate_finalized_review(
                        document,
                        completed_run_number=completed_run_number,
                        run_id=run_id,
                    )
        except FileNotFoundError:
            pass
        except json.JSONDecodeError:
            # A manual editor may briefly expose a partial write. The supplied
            # review script writes atomically, but tolerate this safely.
            pass

        time.sleep(poll_seconds)

def call_reflector(trajectory):
    # Lazy import keeps synthetic/router-only tests independent of the OpenAI
    # package. Real gameplay already requires the package for the actor model.
    from openai import OpenAI

    client = OpenAI(
        timeout=90.0,
        max_retries=2,
    )

    full_input = (
        REFLECTION_PROMPT
        + "\n\n"
        + "=== TRAJECTORY START ===\n"
        + trajectory
        + "\n=== TRAJECTORY END ==="
    )

    started = time.perf_counter()

    response = client.responses.create(
        model=MODEL,
        input=full_input,
    )

    latency_ms = round(
        (time.perf_counter() - started) * 1000,
        2,
    )

    raw_text = response.output_text
    cleaned = strip_code_fence(raw_text)

    try:
        reflection = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "The post-run reflector did not return valid JSON."
        ) from exc

    reflection = validate_reflection(reflection)
    input_tokens, output_tokens = get_usage(response)

    return reflection, raw_text, {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency_ms,
    }


def process_completed_run(
    *,
    completed_run_number,
    run_id,
    events_file,
    states_file,
    memory_file,
    output_dir,
):
    """
    Build the compact trajectory and frozen reflection-v0.2 output, then wait
    for human review before writing any lesson to Condition C memory.

    Crash safety:
    - existing LLM reflection artifacts are reused for the exact same run;
    - the human-review packet is persistent;
    - finalized memory IDs are deterministic and idempotent.
    """
    events_file = Path(events_file)
    states_file = Path(states_file)
    memory_file = Path(memory_file)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    events = load_jsonl(events_file, tolerate_bad_lines=False)
    run_events, run_end = find_run(
        events,
        completed_run_number=completed_run_number,
        run_id=run_id,
    )
    all_states = load_jsonl(states_file, tolerate_bad_lines=True)
    run_states = select_run_state_summaries(all_states, run_events)

    raw_events_path = output_dir / f"run_{completed_run_number:02d}_raw.json"
    states_path = output_dir / f"run_{completed_run_number:02d}_states.json"
    trajectory_path = output_dir / f"run_{completed_run_number:02d}_trajectory_v2.txt"
    reflection_path = output_dir / f"run_{completed_run_number:02d}_reflection_v02.json"
    raw_reflection_path = output_dir / f"run_{completed_run_number:02d}_reflection_v02_raw.txt"
    review_path = output_dir / f"run_{completed_run_number:02d}_human_review.json"

    raw_events_path.write_text(
        json.dumps(run_events, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    states_path.write_text(
        json.dumps(run_states, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    trajectory = build_compact_trajectory(run_events, run_end, run_states)
    trajectory_path.write_text(trajectory, encoding="utf-8")

    reflector_usage = {"input_tokens": None, "output_tokens": None, "latency_ms": None}
    reused_existing_reflection = False

    if reflection_path.exists():
        reflection_document = json.loads(reflection_path.read_text(encoding="utf-8"))
        if (
            reflection_document.get("source_run") != completed_run_number
            or reflection_document.get("source_run_id") != run_id
        ):
            raise ValueError(
                "Existing reflection artifact does not belong to this run: "
                f"{reflection_path}"
            )
        reflection = validate_reflection(
            {
                "summary": reflection_document.get("summary"),
                "lessons": reflection_document.get("lessons"),
            }
        )
        reused_existing_reflection = True
    else:
        reflection, raw_text, reflector_usage = call_reflector(trajectory)
        raw_reflection_path.write_text(raw_text, encoding="utf-8")
        reflection_document = {
            "reflection_version": REFLECTION_VERSION,
            "model": MODEL,
            "source_run": completed_run_number,
            "source_run_id": run_id,
            "trajectory_file": str(trajectory_path),
            "generated_at": utc_now_iso(),
            "summary": reflection["summary"],
            "lessons": reflection["lessons"],
        }
        reflection_path.write_text(
            json.dumps(reflection_document, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    review_document = build_or_load_human_review_packet(
        review_path=review_path,
        completed_run_number=completed_run_number,
        run_id=run_id,
        reflection=reflection,
        trajectory_path=trajectory_path,
        reflection_path=reflection_path,
    )

    if review_document.get("status") != REVIEW_STATUS_FINALIZED:
        review_document = wait_for_human_review(
            review_path,
            completed_run_number=completed_run_number,
            run_id=run_id,
        )
    else:
        review_document = validate_finalized_review(
            review_document,
            completed_run_number=completed_run_number,
            run_id=run_id,
        )

    memory_items, appended_ids = append_human_curated_lessons_idempotently(
        review_document,
        completed_run_number=completed_run_number,
        run_id=run_id,
        memory_file=memory_file,
    )

    counts = {"ACCEPT": 0, "CORRECT": 0, "REJECT": 0, "ADD": 0}
    for item in review_document.get("interventions", []) or []:
        action = str(item.get("action", "")).upper()
        if action in counts:
            counts[action] += 1
    counts["ADD"] = len(review_document.get("added_lessons", []) or [])

    return {
        "completed_run_number": completed_run_number,
        "run_id": run_id,
        "reflection_version": REFLECTION_VERSION,
        "review_version": REVIEW_VERSION,
        "model": MODEL,
        "trajectory_file": str(trajectory_path),
        "reflection_file": str(reflection_path),
        "human_review_file": str(review_path),
        "matched_state_summaries": len(run_states),
        "llm_lesson_count": len(reflection["lessons"]),
        "lesson_count": len(memory_items),
        "memory_ids": [item["id"] for item in memory_items],
        "appended_memory_ids": appended_ids,
        "human_intervention_counts": counts,
        "human_feedback": review_document.get("human_feedback", ""),
        "reused_existing_reflection": reused_existing_reflection,
        "input_tokens": reflector_usage["input_tokens"],
        "output_tokens": reflector_usage["output_tokens"],
        "latency_ms": reflector_usage["latency_ms"],
    }

def find_unprocessed_completed_runs(events_file):
    """
    Return completed RUN_END events that do not yet have a corresponding
    POST_RUN_REFLECTION_COMPLETE event.

    Used after a process restart so a completed run can never be silently
    skipped from the learning sequence.
    """
    events = load_jsonl(
        Path(events_file),
        tolerate_bad_lines=False,
    )

    run_ends = {}
    reflected = set()

    for event in events:
        event_type = event.get("event_type")

        if event_type == "RUN_END":
            number = event.get("completed_run_number")
            if isinstance(number, int):
                run_ends[number] = event

        elif event_type == "POST_RUN_REFLECTION_COMPLETE":
            number = event.get("completed_run_number")
            if isinstance(number, int):
                reflected.add(number)

    pending = []

    for number in sorted(run_ends):
        if number in reflected:
            continue

        event = run_ends[number]
        pending.append(
            {
                "completed_run_number": number,
                "run_id": event.get("run_id"),
            }
        )

    return pending
