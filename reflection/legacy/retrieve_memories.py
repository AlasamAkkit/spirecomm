import json
import sys
from pathlib import Path


MEMORY_FILE = Path("prototype_memory.jsonl")
DEFAULT_TOP_K = 3


def load_memory():
    if not MEMORY_FILE.exists():
        raise FileNotFoundError(
            f"Could not find {MEMORY_FILE}. "
            "Run build_prototype_memory.py first."
        )

    items = []

    with MEMORY_FILE.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} "
                    f"of {MEMORY_FILE}"
                ) from exc

    return items


def decision_type_to_category(decision_type):
    value = decision_type.upper().strip()

    # More specific checks first.
    if "BOSS_REWARD" in value:
        return "BOSS_REWARD"

    if "CARD_REWARD" in value:
        return "CARD_REWARD"

    if "HAND_SELECT" in value:
        return "COMBAT"

    if "COMBAT" in value:
        return "COMBAT"

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

    # Neow, key decisions, unusual screens, etc.
    return "GENERAL"


def retrieve_memories(
    memory_items,
    decision_type,
    top_k=DEFAULT_TOP_K,
):
    category = decision_type_to_category(
        decision_type
    )

    exact = [
        item
        for item in memory_items
        if item.get("category") == category
    ]

    # Keep retrieval deliberately simple and deterministic for the prototype.
    #
    # IMPORTANT CHANGE FROM v0.1:
    # Do NOT fill an exact-category result with unrelated GENERAL memories.
    #
    # If at least one exact-category lesson exists, return only exact-category
    # lessons. GENERAL is used only when there are zero lessons for the mapped
    # category.
    if exact:
        pool = exact
    else:
        pool = [
            item
            for item in memory_items
            if item.get("category") == "GENERAL"
        ]

    # Prototype ranking: newer lessons first.
    #
    # We deliberately do not filter by human judgment or confidence because
    # Condition B must use its self-generated memories autonomously.
    pool.sort(
        key=lambda item: item.get("source_run", -1),
        reverse=True,
    )

    return category, pool[:top_k]


def format_memories_for_prompt(memories):
    if not memories:
        return "No relevant prior lessons."

    lines = [
        "RELEVANT EXPERIENCE FROM PREVIOUS RUNS:",
        (
            "Treat these as learned guidance, not as guaranteed facts. "
            "Apply a lesson only when it fits the current state."
        ),
    ]

    for index, item in enumerate(
        memories,
        start=1,
    ):
        lines.append(
            f"{index}. [{item['category']}] "
            f"{item['title']}"
        )
        lines.append(
            f"   When: {item['situation']}"
        )
        lines.append(
            f"   Lesson: {item['lesson']}"
        )
        lines.append(
            f"   Confidence: {item['confidence']}"
        )

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python retrieve_memories.py "
            "<decision_type> [top_k]"
        )
        print()
        print("Example:")
        print(
            "python retrieve_memories.py "
            "REST_DECISION 3"
        )
        return

    decision_type = sys.argv[1]

    if len(sys.argv) >= 3:
        top_k = int(sys.argv[2])
    else:
        top_k = DEFAULT_TOP_K

    if top_k <= 0:
        raise ValueError("top_k must be greater than 0.")

    memory_items = load_memory()

    category, memories = retrieve_memories(
        memory_items,
        decision_type,
        top_k=top_k,
    )

    print(
        f"Decision type: {decision_type}"
    )
    print(
        f"Mapped category: {category}"
    )
    print(
        f"Retrieved: {len(memories)}"
    )
    print()
    print(
        format_memories_for_prompt(memories)
    )


if __name__ == "__main__":
    main()
