import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI


MODEL = "gpt-5.6-luna"
OUTPUT_DIR = Path("outputs")
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
            if (
                not isinstance(lesson[field], str)
                or not lesson[field].strip()
            ):
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


def load_trajectory(run_number):
    path = (
        OUTPUT_DIR
        / f"run_{run_number:02d}_trajectory_v2.txt"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Could not find {path}. "
            f"Run prepare_reflection.py {run_number} first."
        )

    return path, path.read_text(encoding="utf-8")


def reflect_run(run_number):
    trajectory_path, trajectory = load_trajectory(run_number)

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

    response = client.responses.create(
        model=MODEL,
        input=full_input,
    )

    raw_text = response.output_text
    cleaned = strip_code_fence(raw_text)

    raw_output_path = (
        OUTPUT_DIR
        / f"run_{run_number:02d}_reflection_v02_raw.txt"
    )

    raw_output_path.write_text(
        raw_text,
        encoding="utf-8",
    )

    try:
        reflection = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "The reflector did not return valid JSON. "
            f"Raw output was saved to {raw_output_path}."
        ) from exc

    reflection = validate_reflection(reflection)

    output = {
        "reflection_version": REFLECTION_VERSION,
        "model": MODEL,
        "source_run": run_number,
        "trajectory_file": str(trajectory_path),
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "summary": reflection["summary"],
        "lessons": reflection["lessons"],
    }

    output_path = (
        OUTPUT_DIR
        / f"run_{run_number:02d}_reflection_v02.json"
    )

    output_path.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return output_path, output


def main():
    if len(sys.argv) != 2:
        print("Usage: python reflect_run.py <run_number>")
        return

    try:
        run_number = int(sys.argv[1])
    except ValueError:
        print("Run number must be an integer.")
        return

    try:
        output_path, output = reflect_run(run_number)
    except Exception as exc:
        print(f"Reflection failed: {type(exc).__name__}: {exc}")
        raise

    print(f"Reflection saved: {output_path}")
    print()
    print("Summary:")
    print(output["summary"])
    print()
    print(f"Lessons: {len(output['lessons'])}")

    for index, lesson in enumerate(
        output["lessons"],
        start=1,
    ):
        print(
            f"{index}. [{lesson['category']}] "
            f"{lesson['title']} "
            f"({lesson['confidence']})"
        )

        for evidence in lesson["evidence_points"]:
            print(f"   - {evidence}")

    print()
    print(
        "Prototype mode: nothing was added to memory yet. "
        "Inspect this reflection first."
    )


if __name__ == "__main__":
    main()
