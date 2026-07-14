"""Generate a reference oracle JSONL where each task's code is its reference solution."""

from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_PATH = ROOT / "tasks" / "all_tasks.jsonl"
OUTPUT_PATH = ROOT / "outputs" / "raw_generations" / "reference_oracle.jsonl"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    with TASKS_PATH.open(encoding="utf-8") as f_in, OUTPUT_PATH.open(
        "w", encoding="utf-8"
    ) as f_out:
        for line in f_in:
            task = json.loads(line)
            solution_path = ROOT / task["reference_solution_path"]
            code = solution_path.read_text(encoding="utf-8")
            record = {
                "task_id": task["task_id"],
                "model": "reference_oracle",
                "condition": "gold",
                "temperature": 0.0,
                "max_tokens": 0,
                "prompt_hash": "",
                "prompt": "",
                "raw_output": code,
                "generated_code": code,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "latency": 0.0,
                "prompt_tokens": None,
                "completion_tokens": None,
            }
            f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Wrote reference oracle to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
