"""Build gold and distractor retrieval context files for Nimbla tasks.

Reads the generated Nimbla JSONL task files and produces:
    * v2/retrieval_contexts/gold/nimbla.json
    * v2/retrieval_contexts/distractor/nimbla.json

Each output file is a dict mapping task_id -> list of source strings of the
relevant functions.
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "libs" / "nimbla"))
sys.path.insert(0, str(ROOT / "retrieval_contexts" / "distractor"))

import nimbla
import nimbla_distractor


TASKS_DIR = ROOT / "tasks"
RETRIEVAL_DIR = ROOT / "retrieval_contexts"
RETRIEVAL_DIR.mkdir(parents=True, exist_ok=True)
(GOLD_DIR := RETRIEVAL_DIR / "gold").mkdir(parents=True, exist_ok=True)
(DISTRACTOR_DIR := RETRIEVAL_DIR / "distractor").mkdir(parents=True, exist_ok=True)


def get_source(module: Any, name: str) -> str:
    """Return the source of ``module.name`` or raise a clear error."""
    obj = getattr(module, name)
    return inspect.getsource(obj)


def build() -> None:
    gold: dict[str, list[str]] = {}
    distractor: dict[str, list[str]] = {}

    for level_file in ["nimbla_l1.jsonl", "nimbla_l2.jsonl", "nimbla_l3.jsonl"]:
        path = TASKS_DIR / level_file
        if not path.exists():
            raise FileNotFoundError(f"Task file not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                task = json.loads(line)
                task_id = task["task_id"]
                gold[task_id] = [get_source(nimbla, name) for name in task["gold_snippets"]]
                distractor[task_id] = [
                    get_source(nimbla_distractor, name) for name in task["distractor_snippets"]
                ]

    (GOLD_DIR / "nimbla.json").write_text(
        json.dumps(gold, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (DISTRACTOR_DIR / "nimbla.json").write_text(
        json.dumps(distractor, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Wrote {len(gold)} gold entries to {GOLD_DIR / 'nimbla.json'}")
    print(f"Wrote {len(distractor)} distractor entries to {DISTRACTOR_DIR / 'nimbla.json'}")


if __name__ == "__main__":
    build()
