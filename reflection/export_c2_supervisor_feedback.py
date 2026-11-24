#!/usr/bin/env python3
"""Export a READ-ONLY, reviewed C2 human-feedback snapshot for a supervisor.

This script reads local working feedback/memory/playbook files but never edits
them, imports the gameplay controller, launches a game, or calls the LLM.

Output includes HUMAN_TEACHING verbatim, APPROVE_INITIAL decisions, and any
distinct targeted human corrections found in the raw memory. It deliberately
excludes game trajectories, model prompts, local paths, credentials, run IDs,
and all model-generated reflections not individually approved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFLECTION_DIR = PROJECT_ROOT / "reflection"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "supervisor_materials"
VALID_DECISIONS = {"HUMAN_TEACHING", "APPROVE_INITIAL"}
SUSPICIOUS_TEXT = (
    re.compile(r"(?i)\b(?:sk-proj-|sk-[a-z0-9]{20,})"),
    re.compile(r"(?i)\b(?:api[_ -]?key|password|access[_ -]?token|client[_ -]?secret)\s*[:=]"),
    re.compile(r"(?i)[a-z]:\\(?:users|documents and settings)\\"),
    re.compile(r"(?i)-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----"),
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required local file is missing: {path}")
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {path.name} line {line_number}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"Expected JSON object in {path.name} line {line_number}")
        rows.append(item)
    return rows


def require_reviewed_text(text: str, origin: str) -> None:
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"Missing human teaching in {origin}")
    for pattern in SUSPICIOUS_TEXT:
        if pattern.search(text):
            raise ValueError(
                f"Potential sensitive information in {origin}. "
                "Inspect the source and prepare a separately approved "
                "sanitized copy before publishing; original teaching remains unchanged."
            )


def source_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_snapshot(
    feedback: list[dict[str, Any]],
    memory: list[dict[str, Any]],
    *,
    through_run: int,
    playbook_updated_through: int,
) -> dict[str, Any]:
    """Build a deterministic, minimal supervisor dataset; no file writes."""
    if through_run < 1:
        raise ValueError("through_run must be positive")
    if playbook_updated_through < through_run:
        raise ValueError(
            f"Playbook updated only through Run {playbook_updated_through}; "
            f"requested snapshot through Run {through_run} is not finalized."
        )

    decisions: dict[int, dict[str, Any]] = {}
    for row in feedback:
        source_run = row.get("source_run")
        if isinstance(source_run, bool) or not isinstance(source_run, int):
            raise ValueError("Feedback row has invalid source_run")
        if not 1 <= source_run <= through_run:
            continue
        decision = str(row.get("review_decision") or "").strip().upper()
        if decision not in VALID_DECISIONS:
            raise ValueError(f"Unfinalized/unknown review decision at Run {source_run}")
        if source_run in decisions:
            raise ValueError(f"Duplicate feedback bank entry for Run {source_run}")
        teaching = row.get("human_feedback") or ""
        if not isinstance(teaching, str):
            raise ValueError(f"Invalid feedback text at Run {source_run}")
        if decision == "HUMAN_TEACHING":
            require_reviewed_text(teaching, f"Run {source_run} main teaching")
        elif teaching.strip():
            raise ValueError(
                f"Run {source_run} APPROVE_INITIAL unexpectedly has separate human text"
            )
        decisions[source_run] = {"decision": decision, "text": teaching}

    missing = sorted(set(range(1, through_run + 1)) - set(decisions))
    if missing:
        raise ValueError(
            "Missing finalized feedback bank entries for runs: " +
            ", ".join(map(str, missing))
        )

    by_run: dict[int, list[dict[str, Any]]] = {n: [] for n in decisions}
    for row in memory:
        n = row.get("source_run")
        if isinstance(n, bool) or not isinstance(n, int) or n not in by_run:
            continue
        text = row.get("human_feedback_verbatim")
        if not text:
            continue
        if not row.get("authoritative", False):
            raise ValueError(f"Human text marked non-authoritative at Run {n}")
        require_reviewed_text(text, f"Run {n} memory {row.get('id')}")
        by_run[n].append(row)

    snapshot_runs = []
    targeted_total = 0
    for n in range(1, through_run + 1):
        review = decisions[n]
        main = review["text"]
        distinct: dict[str, dict[str, Any]] = {}
        for lesson in by_run[n]:
            verbatim = lesson["human_feedback_verbatim"]
            if verbatim == main and review["decision"] == "HUMAN_TEACHING":
                continue  # Already represented in the human review bank.
            if verbatim in distinct:
                distinct[verbatim]["source_memory_ids"].append(str(lesson.get("id") or ""))
                continue
            distinct[verbatim] = {
                "human_teaching_verbatim": verbatim,
                "category": str(lesson.get("category") or ""),
                "applies_to": [
                    str(x) for x in (lesson.get("applies_to") or [])
                    if isinstance(x, str)
                ],
                "source_memory_ids": [str(lesson.get("id") or "")],
            }
        targeted_total += len(distinct)
        snapshot_runs.append({
            "run": n,
            "review_decision": review["decision"],
            "human_feedback_verbatim": main if main else None,
            "additional_authoritative_corrections": list(distinct.values()),
        })

    return {
        "schema": "c2-supervisor-feedback-snapshot-v1",
        "research_condition": "C2",
        "scope": "completed and finalized C2 human reviews only",
        "through_run": through_run,
        "playbook_updated_through_run": playbook_updated_through,
        "human_teaching_run_count": sum(
            r["review_decision"] == "HUMAN_TEACHING" for r in snapshot_runs
        ),
        "approved_initial_run_count": sum(
            r["review_decision"] == "APPROVE_INITIAL" for r in snapshot_runs
        ),
        "additional_correction_count": targeted_total,
        "runs": snapshot_runs,
    }


def markdown(snapshot: dict[str, Any]) -> str:
    n = snapshot["through_run"]
    lines = [
        f"# C2 human feedback through Run {n}",
        "",
        "Supervisor review snapshot — authored from finalized local research records.",
        "",
        "Human teaching is preserved verbatim. APPROVE_INITIAL is a human",
        "approval of the model's existing reflection, **not** a new human-written",
        "lesson. Additional authoritative corrections are taken from persistent",
        "raw memory and listed separately. This is a static export, not the live",
        "memory/playbook or a gameplay-performance result.",
        "",
        f"- Finalized run reviews: {n}",
        f"- Runs with direct HUMAN_TEACHING: {snapshot['human_teaching_run_count']}",
        f"- Runs with APPROVE_INITIAL: {snapshot['approved_initial_run_count']}",
        f"- Additional authoritative corrections: {snapshot['additional_correction_count']}",
        "",
        "Original private identifiers, file paths, generated model reflections,",
        "gameplay logs, and credentials are intentionally excluded.",
        "",
    ]
    for row in snapshot["runs"]:
        index = row["run"]
        decision = row["review_decision"]
        lines += [f"## Run {index:02d} — {decision}", ""]
        if decision == "HUMAN_TEACHING":
            lines += ["**Human's verbatim feedback:**", ""]
            lines.extend("    " + l for l in row["human_feedback_verbatim"].split("\n"))
            lines += [""]
        else:
            lines += ["Human approved the initial model reflection; no separate",
                      "run-level human teaching text was submitted.", ""]
        for j, extra in enumerate(row["additional_authoritative_corrections"], 1):
            lines += [f"**Additional authoritative correction {j}:**", ""]
            lines.extend(
                "    " + l for l in extra["human_teaching_verbatim"].split("\n")
            )
            lines += [""]
    return "\n".join(lines).rstrip() + "\n"


def write_snapshot(output_dir: Path, snapshot: dict[str, Any]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"c2_human_feedback_through_run{snapshot['through_run']:02d}"
    md = output_dir / (stem + ".md")
    js = output_dir / (stem + ".json")
    # Both are derived publication copies; never write into reflection/.
    md.write_text(markdown(snapshot), encoding="utf-8")
    js.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8")
    return md, js


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--through-run", type=int, default=56)
    parser.add_argument("--reflection-dir", type=Path, default=REFLECTION_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    reflection = args.reflection_dir.resolve()
    sources = {
        "feedback": reflection / "condition_c2_feedback.jsonl",
        "memory": reflection / "condition_c2_raw_memory.jsonl",
        "playbook": reflection / "condition_c2_playbook.json",
    }
    reviews = load_jsonl(sources["feedback"])
    lessons = load_jsonl(sources["memory"])
    if not sources["playbook"].is_file():
        raise FileNotFoundError(sources["playbook"])
    playbook = json.loads(sources["playbook"].read_text(encoding="utf-8"))
    if not isinstance(playbook, dict):
        raise ValueError("Invalid playbook JSON object")
    snapshot = build_snapshot(
        reviews, lessons, through_run=args.through_run,
        playbook_updated_through=int(playbook.get("updated_through_run") or 0),
    )
    if args.validate_only:
        print("VALIDATION OK (no output written)")
    else:
        md, js = write_snapshot(args.output_dir.resolve(), snapshot)
        print("Generated supervisor snapshot:")
        print(md)
        print(js)
    print(
        f"Reviews={len(snapshot['runs'])}, "
        f"human_teaching={snapshot['human_teaching_run_count']}, "
        f"approved_initial={snapshot['approved_initial_run_count']}, "
        f"additional_corrections={snapshot['additional_correction_count']}"
    )
    print("Inspect the output for appropriateness before committing.")
    print("Active memory, feedback, playbook and game logs were not modified.")


if __name__ == "__main__":
    main()
