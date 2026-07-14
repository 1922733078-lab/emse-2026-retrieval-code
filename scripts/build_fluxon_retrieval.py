"""Build retrieval context files for Fluxon tasks.

Reads the generated JSONL task files and produces two JSON maps:
  * retrieval_contexts/gold/fluxon.json      -> task_id -> list of gold function sources
  * retrieval_contexts/distractor/fluxon.json -> task_id -> list of distractor function sources
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "libs" / "fluxon"))
sys.path.insert(0, str(ROOT / "retrieval_contexts" / "distractor"))

import fluxon
import fluxon_distractor

TASK_FILES = [
    ROOT / "tasks" / "fluxon_l1.jsonl",
    ROOT / "tasks" / "fluxon_l2.jsonl",
    ROOT / "tasks" / "fluxon_l3.jsonl",
]

GOLD_DIR = ROOT / "retrieval_contexts" / "gold"
DISTRACTOR_DIR = ROOT / "retrieval_contexts" / "distractor"
GOLD_DIR.mkdir(parents=True, exist_ok=True)
DISTRACTOR_DIR.mkdir(parents=True, exist_ok=True)


def _sources(module: object, names: list[str]) -> list[str]:
    sources: list[str] = []
    for name in names:
        func = getattr(module, name, None)
        if func is None:
            raise ValueError(f"Function {name!r} not found in {module.__name__}")
        sources.append(inspect.getsource(func))
    return sources


def main() -> None:
    gold: dict[str, list[str]] = {}
    distractor: dict[str, list[str]] = {}

    for path in TASK_FILES:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                task = json.loads(line)
                tid = task["task_id"]
                gold[tid] = _sources(fluxon, task["gold_snippets"])
                distractor[tid] = _sources(fluxon_distractor, task["distractor_snippets"])

    gold_path = GOLD_DIR / "fluxon.json"
    with gold_path.open("w", encoding="utf-8") as f:
        json.dump(gold, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(gold)} gold contexts to {gold_path}")

    distractor_path = DISTRACTOR_DIR / "fluxon.json"
    with distractor_path.open("w", encoding="utf-8") as f:
        json.dump(distractor, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(distractor)} distractor contexts to {distractor_path}")


if __name__ == "__main__":
    main()
