"""Interactive reviewer for Condition C human-feedback episodes.

Run this in a SECOND terminal after an episode ends:

    python reflection/review_condition_c.py

The gameplay controller waits for the pending review JSON to become FINALIZED.
This script never talks to CommunicationMod and may safely use stdin/stdout.
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from condition_c_reflection import (
    ALLOWED_CATEGORIES,
    ALLOWED_CONFIDENCE,
    ALLOWED_REASON_CODES,
    REVIEW_STATUS_FINALIZED,
    REVIEW_STATUS_PENDING,
    REVIEW_VERSION,
    validate_reflection,
)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "condition_c_outputs"

REASON_CHOICES = [
    "WRONG_CAUSE",
    "MISSED_INSIGHT",
    "TOO_VAGUE",
    "FALSE_LESSON",
    "LONG_HORIZON_PLANNING",
    "OTHER",
]


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path, document):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, path)


def find_pending(output_dir, run_number=None):
    output_dir = Path(output_dir)
    if not output_dir.exists():
        raise SystemExit(f"No Condition C output directory found: {output_dir}")

    paths = sorted(output_dir.glob("run_*_human_review.json"))
    pending = []
    for path in paths:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if run_number is not None and doc.get("source_run") != run_number:
            continue
        if doc.get("status") == REVIEW_STATUS_PENDING:
            pending.append((path, doc))

    if not pending:
        if run_number is None:
            raise SystemExit("No pending Condition C human review found.")
        raise SystemExit(f"No pending review found for completed run {run_number}.")

    return pending[0]


def prompt_choice(prompt, choices):
    mapping = {str(i + 1): value for i, value in enumerate(choices)}
    while True:
        print(prompt)
        for i, value in enumerate(choices, start=1):
            print(f"  {i}. {value}")
        answer = input("> ").strip()
        if answer in mapping:
            return mapping[answer]
        upper = answer.upper()
        if upper in choices:
            return upper
        print("Invalid choice.\n")


def prompt_text(label, default=None, required=True):
    while True:
        suffix = f" [{default}]" if default not in (None, "") else ""
        value = input(f"{label}{suffix}: ").strip()
        if not value and default not in (None, ""):
            return default
        if value:
            return value
        if not required:
            return "" if default is None else default
        print("A value is required.")


def prompt_reason():
    return prompt_choice("Reason for this human intervention:", REASON_CHOICES)


def display_lesson(index, lesson):
    print("\n" + "=" * 72)
    print(f"LLM LESSON {index}")
    print("=" * 72)
    print(f"Category:   {lesson.get('category')}")
    print(f"Title:      {lesson.get('title')}")
    print(f"Situation:  {lesson.get('situation')}")
    print(f"Lesson:     {lesson.get('lesson')}")
    print("Evidence:")
    for e in lesson.get("evidence_points", []) or []:
        print(f"  - {e}")
    print(f"Reasoning:  {lesson.get('reasoning')}")
    print(f"Confidence: {lesson.get('confidence')}")


def edit_lesson(original=None):
    """Edit only the fields the reviewer explicitly selects.

    This avoids accidentally overwriting multiple lesson fields while trying
    to answer a yes/no prompt. Unselected fields are preserved exactly.
    """
    original = dict(original or {})

    if not original:
        # Human-added lesson: all fields are required.
        category = prompt_text(
            "Category " + "/".join(sorted(ALLOWED_CATEGORIES)),
            "GENERAL",
        ).upper()
        while category not in ALLOWED_CATEGORIES:
            print("Invalid category.")
            category = prompt_text("Category", "GENERAL").upper()

        title = prompt_text("Title")
        situation = prompt_text("Situation")
        lesson_text = prompt_text("Lesson")

        evidence_input = input("Enter 1-3 evidence points separated by |: ").strip()
        evidence = [p.strip() for p in evidence_input.split("|") if p.strip()]
        while not (1 <= len(evidence) <= 3):
            evidence_input = input("Enter 1-3 evidence points separated by |: ").strip()
            evidence = [p.strip() for p in evidence_input.split("|") if p.strip()]

        reasoning = prompt_text("Reasoning")
        confidence = prompt_text("Confidence (low/medium/high)", "medium").lower()
        while confidence not in ALLOWED_CONFIDENCE:
            print("Invalid confidence.")
            confidence = prompt_text("Confidence", "medium").lower()

        candidate = {
            "category": category,
            "title": title,
            "situation": situation,
            "lesson": lesson_text,
            "evidence_points": evidence,
            "reasoning": reasoning,
            "confidence": confidence,
        }
        validate_reflection({"summary": "review", "lessons": [candidate]})
        return candidate

    candidate = {
        "category": str(original.get("category", "GENERAL")).upper(),
        "title": original.get("title", ""),
        "situation": original.get("situation", ""),
        "lesson": original.get("lesson", ""),
        "evidence_points": list(original.get("evidence_points", []) or []),
        "reasoning": original.get("reasoning", ""),
        "confidence": str(original.get("confidence", "medium")).lower(),
    }

    print("\nWhich fields do you want to change?")
    print("  1. Category")
    print("  2. Title")
    print("  3. Situation")
    print("  4. Lesson")
    print("  5. Evidence points")
    print("  6. Reasoning")
    print("  7. Confidence")
    print("Example: 4        -> change only the lesson text")
    print("         3,4,6    -> change situation, lesson, and reasoning")

    while True:
        raw = input("Fields to edit (comma-separated): ").strip()
        try:
            fields = {int(x.strip()) for x in raw.split(",") if x.strip()}
        except ValueError:
            fields = set()
        if fields and fields.issubset(set(range(1, 8))):
            break
        print("Choose one or more numbers from 1-7.")

    if 1 in fields:
        category = prompt_text(
            "New category " + "/".join(sorted(ALLOWED_CATEGORIES)),
            candidate["category"],
        ).upper()
        while category not in ALLOWED_CATEGORIES:
            print("Invalid category.")
            category = prompt_text("New category", candidate["category"]).upper()
        candidate["category"] = category

    if 2 in fields:
        candidate["title"] = prompt_text("New title", candidate["title"])

    if 3 in fields:
        candidate["situation"] = prompt_text("New situation", candidate["situation"])

    if 4 in fields:
        candidate["lesson"] = prompt_text("New lesson", candidate["lesson"])

    if 5 in fields:
        print("Current evidence points:")
        for i, evidence in enumerate(candidate["evidence_points"], start=1):
            print(f"  {i}. {evidence}")
        evidence_input = input("New 1-3 evidence points separated by |: ").strip()
        evidence = [p.strip() for p in evidence_input.split("|") if p.strip()]
        while not (1 <= len(evidence) <= 3):
            evidence_input = input("Enter 1-3 evidence points separated by |: ").strip()
            evidence = [p.strip() for p in evidence_input.split("|") if p.strip()]
        candidate["evidence_points"] = evidence

    if 6 in fields:
        candidate["reasoning"] = prompt_text("New reasoning", candidate["reasoning"])

    if 7 in fields:
        confidence = prompt_text(
            "New confidence (low/medium/high)",
            candidate["confidence"],
        ).lower()
        while confidence not in ALLOWED_CONFIDENCE:
            print("Invalid confidence.")
            confidence = prompt_text(
                "New confidence",
                candidate["confidence"],
            ).lower()
        candidate["confidence"] = confidence

    # Guard against the most common interactive-input mistake from the smoke test.
    for field in ("title", "situation", "lesson"):
        value = str(candidate.get(field, "")).strip().lower()
        if value in {"y", "yes", "n", "no"}:
            raise ValueError(
                f"{field!r} was set to {candidate[field]!r}. "
                "This looks like an accidental yes/no response. "
                "Run the reviewer again and edit the intended field."
            )

    validate_reflection({"summary": "review", "lessons": [candidate]})
    return candidate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=int, default=None, help="Completed run number")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=(
            "Directory containing Condition C review packets. "
            "Relative paths are resolved from the current working directory."
        ),
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir

    path, doc = find_pending(output_dir, args.run)

    print("\n" + "#" * 72)
    print(f"CONDITION C HUMAN REVIEW — COMPLETED RUN {doc.get('source_run')}")
    print("#" * 72)
    print(f"Review file:   {path}")
    print(f"Trajectory:    {doc.get('trajectory_file')}")
    print(f"LLM reflection:{doc.get('reflection_file')}")
    print("\nLLM run summary:")
    print(doc.get("llm_summary", ""))
    print(
        "\nRule: at most 3 FINAL lessons may be stored. "
        "Use the trajectory when correcting causal claims."
    )

    final_lessons = []
    interventions = []

    for index, original in enumerate(doc.get("llm_lessons", []) or [], start=1):
        display_lesson(index, original)

        if len(final_lessons) >= 3:
            print("Final lesson capacity already reached; remaining LLM lesson must be rejected.")
            action = "REJECT"
        else:
            action = prompt_choice(
                "Human decision for this lesson:",
                ["ACCEPT", "CORRECT", "REJECT"],
            )

        intervention = {
            "original_lesson_index": index,
            "action": action,
            "reason_code": "ACCEPT" if action == "ACCEPT" else None,
            "note": "",
            "final_lesson_index": None,
        }

        if action == "ACCEPT":
            final_lessons.append(original)
            intervention["final_lesson_index"] = len(final_lessons)

        elif action == "CORRECT":
            intervention["reason_code"] = prompt_reason()
            intervention["note"] = prompt_text(
                "Short note explaining your correction", required=False, default=""
            )
            corrected = edit_lesson(original)
            final_lessons.append(corrected)
            intervention["final_lesson_index"] = len(final_lessons)

        elif action == "REJECT":
            intervention["reason_code"] = prompt_reason()
            intervention["note"] = prompt_text(
                "Short note explaining rejection", required=False, default=""
            )

        interventions.append(intervention)

    added_lessons = []
    while len(final_lessons) < 3:
        add = input(
            f"\nAdd your own missing lesson? ({len(final_lessons)}/3 final lessons) [y/N]: "
        ).strip().lower()
        if add not in {"y", "yes"}:
            break

        reason = prompt_choice(
            "Reason for adding a human-written lesson:",
            ["MISSED_INSIGHT", "LONG_HORIZON_PLANNING", "OTHER"],
        )
        note = prompt_text(
            "Short note explaining what the LLM missed", required=False, default=""
        )
        lesson = edit_lesson(None)
        final_lessons.append(lesson)
        added_lessons.append(
            {
                "action": "ADD",
                "reason_code": reason,
                "note": note,
                "final_lesson_index": len(final_lessons),
            }
        )

    print("\n" + "=" * 72)
    print("FINAL MEMORY PREVIEW")
    print("=" * 72)
    if not final_lessons:
        print("No lessons will be stored for this run.")
    else:
        for i, lesson in enumerate(final_lessons, start=1):
            print(f"\n{i}. [{lesson['category']}] {lesson['title']}")
            print(f"   Situation: {lesson['situation']}")
            print(f"   Lesson:    {lesson['lesson']}")
            print("   Evidence:")
            for evidence in lesson.get("evidence_points", []) or []:
                print(f"     - {evidence}")
            print(f"   Reasoning: {lesson['reasoning']}")
            print(f"   Confidence: {lesson['confidence']}")

    human_feedback = prompt_text(
        "\nOptional overall feedback for this episode",
        required=False,
        default="",
    )

    confirm = input("Finalize this review and allow the next run? [y/N]: ").strip().lower()
    if confirm not in {"y", "yes"}:
        print("Review NOT finalized. Run this script again when ready.")
        return

    validate_reflection(
        {
            "summary": doc.get("llm_summary") or "Human-reviewed run lessons.",
            "lessons": final_lessons,
        }
    )

    doc["review_version"] = REVIEW_VERSION
    doc["status"] = REVIEW_STATUS_FINALIZED
    doc["reviewed_at"] = utc_now_iso()
    doc["human_feedback"] = human_feedback
    doc["interventions"] = interventions
    doc["added_lessons"] = added_lessons
    doc["final_lessons"] = final_lessons

    atomic_write_json(path, doc)
    print(f"\nFinalized: {path}")
    print("The gameplay controller should detect this automatically and continue.")


if __name__ == "__main__":
    main()
