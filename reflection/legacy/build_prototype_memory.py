import json
import re
from pathlib import Path


OUTPUT_DIR = Path("outputs")
MEMORY_FILE = Path("prototype_memory.jsonl")

REFLECTION_PATTERN = re.compile(
    r"run_(\d+)_reflection_v02\.json$"
)


def load_reflection_files():
    files = []

    for path in OUTPUT_DIR.glob("run_*_reflection_v02.json"):
        match = REFLECTION_PATTERN.match(path.name)

        if not match:
            continue

        run_number = int(match.group(1))
        files.append((run_number, path))

    files.sort(key=lambda item: item[0])

    return files


def validate_reflection_file(data, path):
    required_top_level = {
        "reflection_version",
        "model",
        "source_run",
        "summary",
        "lessons",
    }

    missing = required_top_level - data.keys()

    if missing:
        raise ValueError(
            f"{path} is missing fields: "
            + ", ".join(sorted(missing))
        )

    if not isinstance(data["lessons"], list):
        raise ValueError(
            f"{path}: 'lessons' must be a list."
        )


def make_memory_item(
    reflection,
    lesson,
    lesson_number,
):
    source_run = int(reflection["source_run"])

    return {
        "id": f"self_run_{source_run:02d}_{lesson_number:02d}",
        "source": "self",
        "source_run": source_run,
        "reflection_version": reflection["reflection_version"],
        "model": reflection["model"],
        "category": lesson["category"],
        "title": lesson["title"],
        "situation": lesson["situation"],
        "lesson": lesson["lesson"],
        "evidence_points": lesson["evidence_points"],
        "reasoning": lesson["reasoning"],
        "confidence": lesson["confidence"],
    }


def build_prototype_memory():
    reflection_files = load_reflection_files()

    if not reflection_files:
        raise FileNotFoundError(
            "No files matching "
            "outputs/run_*_reflection_v02.json were found."
        )

    memory_items = []

    for _, path in reflection_files:
        with path.open("r", encoding="utf-8") as f:
            reflection = json.load(f)

        validate_reflection_file(
            reflection,
            path,
        )

        for lesson_number, lesson in enumerate(
            reflection["lessons"],
            start=1,
        ):
            memory_items.append(
                make_memory_item(
                    reflection,
                    lesson,
                    lesson_number,
                )
            )

    # Prototype behavior:
    # rebuild from scratch every time so rerunning this script
    # never duplicates lessons.
    with MEMORY_FILE.open("w", encoding="utf-8") as f:
        for item in memory_items:
            f.write(
                json.dumps(
                    item,
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(
        f"Prototype memory built: {MEMORY_FILE}"
    )
    print(
        f"Reflection files used: {len(reflection_files)}"
    )
    print(
        f"Memory items stored: {len(memory_items)}"
    )

    print()
    print("Runs included:")

    for run_number, path in reflection_files:
        print(f"  Run {run_number}: {path.name}")


if __name__ == "__main__":
    build_prototype_memory()
