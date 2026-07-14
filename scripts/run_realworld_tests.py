"""Execute generated code for real-world E9 tasks against their tests."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, TimeoutError
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def classify_error(exc: Exception, test: str) -> str:
    name = type(exc).__name__
    if name == "AssertionError":
        return "Assertion Error"
    if name == "NameError":
        return "Missing Dependency"
    if name in ("TypeError", "ValueError"):
        return "Runtime Error"
    if name == "SyntaxError":
        return "Syntax Error"
    return name


def run_code(
    code: str,
    visible_tests: list[str],
    hidden_tests: list[str],
) -> dict[str, Any]:
    """Run generated code against tests. Executed inside worker subprocess."""
    # Make real-world packages importable for generated code.
    sys.path.insert(0, str(ROOT / "realworld" / "repos" / "python-dateutil" / "src"))
    sys.path.insert(0, str(ROOT / "realworld" / "repos" / "humanize" / "src"))
    sys.path.insert(0, str(ROOT / "realworld" / "repos" / "tabulate"))

    import dateutil
    import humanize
    import tabulate

    namespace: dict[str, Any] = {}
    for module in (dateutil, humanize, tabulate):
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

    try:
        exec(code, namespace)
    except SyntaxError as e:
        result["error_type"] = "Syntax Error"
        result["error_message"] = f"{e}\n{traceback.format_exc()}"
        return result
    except Exception as e:
        result["error_type"] = "Execution Error"
        result["error_message"] = f"{e}\n{traceback.format_exc()}"
        return result

    if "solve" not in namespace or not callable(namespace["solve"]):
        result["error_type"] = "Missing solve function"
        result["error_message"] = "Generated code does not define a callable 'solve'."
        return result

    for test in visible_tests:
        try:
            exec(test, namespace)
        except Exception as e:
            result["error_type"] = classify_error(e, test)
            result["error_message"] = f"{e}\n{traceback.format_exc()}"
            result["first_failed_test"] = test
            return result
    result["visible_passed"] = True

    for test in hidden_tests:
        try:
            exec(test, namespace)
        except Exception as e:
            result["error_type"] = classify_error(e, test)
            result["error_message"] = f"{e}\n{traceback.format_exc()}"
            result["first_failed_test"] = test
            return result
    result["hidden_passed"] = True

    result["passed"] = True
    return result


def evaluate_record(record: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    code = record["generated_code"]
    test_result = run_code(code, task["visible_tests"], task["hidden_tests"])
    record.update(test_result)
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Generations JSONL")
    parser.add_argument("output", type=Path, help="Output test results JSONL")
    parser.add_argument(
        "--tasks",
        type=Path,
        default=ROOT / "realworld" / "tasks" / "realworld_tasks_final.jsonl",
        help="Task definitions JSONL",
    )
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    records: list[dict[str, Any]] = []
    with args.input.open(encoding="utf-8") as f_in:
        for line in f_in:
            records.append(json.loads(line))

    tasks: dict[str, dict[str, Any]] = {}
    with args.tasks.open(encoding="utf-8") as f:
        for line in f:
            task = json.loads(line)
            tasks[task["task_id"]] = task

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f_out, ProcessPoolExecutor(
        max_workers=args.workers
    ) as executor:
        futures = {
            executor.submit(evaluate_record, rec, tasks[rec["task_id"]]): rec
            for rec in records
        }
        for future in futures:
            try:
                result = future.result(timeout=args.timeout)
            except TimeoutError:
                rec = futures[future]
                result = dict(rec)
                result.update(
                    {
                        "passed": False,
                        "visible_passed": False,
                        "hidden_passed": False,
                        "error_type": "Timeout",
                        "error_message": "Record evaluation timed out",
                        "first_failed_test": None,
                    }
                )
            except Exception as e:
                rec = futures[future]
                result = dict(rec)
                result.update(
                    {
                        "passed": False,
                        "visible_passed": False,
                        "hidden_passed": False,
                        "error_type": "Evaluation Error",
                        "error_message": f"{e}\n{traceback.format_exc()}",
                        "first_failed_test": None,
                    }
                )
            f_out.write(json.dumps(result, ensure_ascii=False) + "\n")

    print(f"Wrote test results to {args.output}")


if __name__ == "__main__":
    main()
