"""Build gold and distractor retrieval contexts for Quorix tasks.

Reads the generated task JSONL files and produces:
    retrieval_contexts/gold/quorix.json
    retrieval_contexts/distractor/quorix.json

Each file maps task_id -> list of source strings for the referenced functions.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
GOLD_DIR = ROOT / "retrieval_contexts" / "gold"
DISTRACTOR_DIR = ROOT / "retrieval_contexts" / "distractor"

GOLD_DIR.mkdir(parents=True, exist_ok=True)
DISTRACTOR_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Load the real library and the distractor module by path
# ---------------------------------------------------------------------------

gold_spec = importlib.util.spec_from_file_location(
    "quorix", ROOT / "libs" / "quorix" / "quorix.py"
)
quorix = importlib.util.module_from_spec(gold_spec)
gold_spec.loader.exec_module(quorix)

dist_spec = importlib.util.spec_from_file_location(
    "quorix_distractor", ROOT / "retrieval_contexts" / "distractor" / "quorix_distractor.py"
)
quorix_distractor = importlib.util.module_from_spec(dist_spec)
dist_spec.loader.exec_module(quorix_distractor)


def get_source(module: Any, name: str) -> str:
    """Return the source of ``name`` from ``module`` or an error placeholder."""
    obj = getattr(module, name, None)
    if obj is None:
        return f"# Source not found for {name}\n"
    try:
        return inspect.getsource(obj)
    except (OSError, TypeError) as exc:
        return f"# Could not extract source for {name}: {exc}\n"


def main() -> None:
    all_tasks_path = TASKS_DIR / "quorix_all.jsonl"
    tasks: list[dict[str, Any]] = []
    with all_tasks_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))

    gold_contexts: dict[str, list[str]] = {}
    distractor_contexts: dict[str, list[str]] = {}

    for task in tasks:
        tid = task["task_id"]
        gold_contexts[tid] = [
            get_source(quorix, name) for name in task["gold_snippets"]
        ]
        distractor_contexts[tid] = [
            get_source(quorix_distractor, name) for name in task["distractor_snippets"]
        ]

    gold_path = GOLD_DIR / "quorix.json"
    with gold_path.open("w", encoding="utf-8") as f:
        json.dump(gold_contexts, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(gold_contexts)} gold contexts to {gold_path}")

    distractor_path = DISTRACTOR_DIR / "quorix.json"
    with distractor_path.open("w", encoding="utf-8") as f:
        json.dump(distractor_contexts, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(distractor_contexts)} distractor contexts to {distractor_path}")


if __name__ == "__main__":
    main()
