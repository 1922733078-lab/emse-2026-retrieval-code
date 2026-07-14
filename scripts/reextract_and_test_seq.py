"""Re-extract code and rerun tests sequentially, skipping known segfault tasks."""

from __future__ import annotations

import json
import signal
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "libs" / "fluxon"))
sys.path.insert(0, str(ROOT / "libs" / "quorix"))
sys.path.insert(0, str(ROOT / "libs" / "nimbla"))

import fluxon
import nimbla
import quorix
import run_generation


def timeout_handler(signum, frame):
    raise TimeoutError("record evaluation timed out")


def evaluate_record(record: dict, task: dict, timeout: int = 15) -> dict:
    code = run_generation.extract_code(record.get("raw_output", ""))
    record["generated_code"] = code

    namespace: dict = {}
    for module in (fluxon, quorix, nimbla):
        for name in dir(module):
            if not name.startswith("_"):
                namespace[name] = getattr(module, name)

    result = {
        "passed": False,
        "visible_passed": False,
        "hidden_passed": False,
        "error_type": None,
        "error_message": None,
        "first_failed_test": None,
    }

    old = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    try:
        try:
            exec(code, namespace)
        except SyntaxError as e:
            result["error_type"] = "Syntax Error"
            result["error_message"] = f"{e}"
            record.update(result)
            return record
        except Exception as e:
            result["error_type"] = "Execution Error"
            result["error_message"] = f"{e}"
            record.update(result)
            return record

        if "solve" not in namespace or not callable(namespace["solve"]):
            result["error_type"] = "Missing solve function"
            result["error_message"] = "Generated code does not define a callable 'solve'."
            record.update(result)
            return record

        for test in task["visible_tests"]:
            try:
                exec(test, namespace)
            except Exception as e:
                result["error_type"] = type(e).__name__
                result["error_message"] = f"{e}"
                result["first_failed_test"] = test
                record.update(result)
                return record
        result["visible_passed"] = True

        for test in task["hidden_tests"]:
            try:
                exec(test, namespace)
            except Exception as e:
                result["error_type"] = type(e).__name__
                result["error_message"] = f"{e}"
                result["first_failed_test"] = test
                record.update(result)
                return record
        result["hidden_passed"] = True
        result["passed"] = True
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)

    record.update(result)
    return record


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--skip-tasks", nargs="+", default=[])
    args = parser.parse_args()

    records = []
    with args.raw.open(encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    tasks: dict[str, dict] = {}
    with (ROOT / "tasks" / "all_tasks.jsonl").open(encoding="utf-8") as f:
        for line in f:
            t = json.loads(line)
            tasks[t["task_id"]] = t

    skip_set = set(args.skip_tasks)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f_out:
        for i, rec in enumerate(records):
            if rec["task_id"] in skip_set:
                rec["generated_code"] = run_generation.extract_code(rec.get("raw_output", ""))
                rec.update(
                    {
                        "passed": False,
                        "visible_passed": False,
                        "hidden_passed": False,
                        "error_type": "Skipped (segfault risk)",
                        "error_message": "Skipped due to known segfault risk",
                        "first_failed_test": None,
                    }
                )
            else:
                rec = evaluate_record(rec, tasks[rec["task_id"]])
            f_out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if (i + 1) % 500 == 0:
                print(f"Processed {i + 1}/{len(records)}", flush=True)

    print(f"Wrote {len(records)} test results to {args.output}")


if __name__ == "__main__":
    main()
