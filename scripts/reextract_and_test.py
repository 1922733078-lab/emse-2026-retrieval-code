"""Re-extract code from raw generations using the latest extractor and rerun tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "libs" / "fluxon"))
sys.path.insert(0, str(ROOT / "libs" / "quorix"))
sys.path.insert(0, str(ROOT / "libs" / "nimbla"))

import run_generation
import run_tests


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    records = []
    with args.raw.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            rec["generated_code"] = run_generation.extract_code(rec.get("raw_output", ""))
            records.append(rec)

    tasks: dict[str, dict] = {}
    with (ROOT / "tasks" / "all_tasks.jsonl").open(encoding="utf-8") as f:
        for line in f:
            t = json.loads(line)
            tasks[t["task_id"]] = t

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f_out:
        for rec in records:
            task = tasks[rec["task_id"]]
            result = run_tests.run_code(
                rec["generated_code"], task["visible_tests"], task["hidden_tests"]
            )
            rec.update(result)
            f_out.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} test results to {args.output}")


if __name__ == "__main__":
    main()
