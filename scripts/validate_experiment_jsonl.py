"""Validate raw generation and test result JSONL files for an experiment run.

Returns exit code 0 if all checks pass, non-zero otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_RAW_FIELDS = {
    "task_id",
    "model",
    "model_alias",
    "backend",
    "condition",
    "strategy",
    "sample_id",
    "seed",
    "temperature",
    "top_p",
    "max_tokens",
    "thinking",
    "prompt_hash",
    "raw_output",
    "generated_code",
    "timestamp",
    "response_model",
    "response_id",
    "finish_reason",
}

REQUIRED_TEST_FIELDS = REQUIRED_RAW_FIELDS | {
    "passed",
    "visible_passed",
    "hidden_passed",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{line_number}: JSON parse error: {e}")
    return records


def validate_raw(
    path: Path,
    expected_tasks: set[str],
    expected_conditions: set[str],
    expected_samples: int,
    expected_strategy: str = "standard",
) -> list[str]:
    errors: list[str] = []
    try:
        records = load_jsonl(path)
    except ValueError as e:
        return [str(e)]

    if not records:
        errors.append(f"{path}: no records found")
        return errors

    seen_keys: set[tuple[str, str, str, int]] = set()
    prompt_hashes: dict[tuple[str, str, str], str] = {}
    for idx, rec in enumerate(records, start=1):
        missing = REQUIRED_RAW_FIELDS - set(rec.keys())
        if missing:
            errors.append(f"{path}:{idx}: missing fields {sorted(missing)}")
            continue

        if not rec.get("generated_code"):
            errors.append(f"{path}:{idx}: generated_code is empty")

        if rec.get("error"):
            errors.append(f"{path}:{idx}: unresolved API error: {rec['error']}")

        finish_reason = rec.get("finish_reason")
        if finish_reason is not None and finish_reason not in {"stop", "length", "content_filter"}:
            errors.append(f"{path}:{idx}: unexpected finish_reason {finish_reason!r}")

        key = (
            rec.get("task_id", ""),
            rec.get("condition", ""),
            rec.get("strategy", "standard"),
            rec.get("sample_id", 0),
        )
        if key in seen_keys:
            errors.append(f"{path}:{idx}: duplicate key {key}")
        seen_keys.add(key)

        # Prompt hash must be identical across sample_ids for the same (task, condition, strategy).
        hash_key = key[:3]
        ph = rec.get("prompt_hash")
        if ph is not None:
            if hash_key in prompt_hashes and prompt_hashes[hash_key] != ph:
                errors.append(f"{path}:{idx}: prompt_hash mismatch for {hash_key}")
            prompt_hashes[hash_key] = ph

    # Completeness check.
    actual_keys = {
        (r.get("task_id"), r.get("condition"), r.get("strategy", "standard"), r.get("sample_id", 0))
        for r in records
    }
    expected_keys = {
        (task, cond, expected_strategy, sample)
        for task in expected_tasks
        for cond in expected_conditions
        for sample in range(expected_samples)
    }
    missing_keys = expected_keys - actual_keys
    if missing_keys:
        sample = sorted(missing_keys)[:5]
        errors.append(f"{path}: missing {len(missing_keys)} expected keys, e.g. {sample}")

    unexpected_conditions = {r.get("condition") for r in records} - expected_conditions
    if unexpected_conditions:
        errors.append(f"{path}: unexpected conditions {sorted(unexpected_conditions)}")

    return errors


def validate_tested(
    path: Path,
    raw_records: list[dict[str, Any]],
    expected_tasks: set[str],
    expected_conditions: set[str],
    expected_samples: int,
    expected_strategy: str = "standard",
) -> list[str]:
    errors: list[str] = []
    try:
        records = load_jsonl(path)
    except ValueError as e:
        return [str(e)]

    if not records:
        errors.append(f"{path}: no records found")
        return errors

    seen_keys: set[tuple[str, str, str, int]] = set()
    for idx, rec in enumerate(records, start=1):
        missing = REQUIRED_TEST_FIELDS - set(rec.keys())
        if missing:
            errors.append(f"{path}:{idx}: missing fields {sorted(missing)}")
            continue

        key = (
            rec.get("task_id", ""),
            rec.get("condition", ""),
            rec.get("strategy", "standard"),
            rec.get("sample_id", 0),
        )
        if key in seen_keys:
            errors.append(f"{path}:{idx}: duplicate key {key}")
        seen_keys.add(key)

    # Completeness.
    actual_keys = {
        (r.get("task_id"), r.get("condition"), r.get("strategy", "standard"), r.get("sample_id", 0))
        for r in records
    }
    expected_keys = {
        (task, cond, expected_strategy, sample)
        for task in expected_tasks
        for cond in expected_conditions
        for sample in range(expected_samples)
    }
    missing_keys = expected_keys - actual_keys
    if missing_keys:
        sample = sorted(missing_keys)[:5]
        errors.append(f"{path}: missing {len(missing_keys)} expected keys, e.g. {sample}")

    # Raw/test key match.
    raw_keys = {
        (r.get("task_id"), r.get("condition"), r.get("strategy", expected_strategy), r.get("sample_id", 0))
        for r in raw_records
    }
    unmatched = actual_keys - raw_keys
    if unmatched:
        sample = sorted(unmatched)[:5]
        errors.append(f"{path}: {len(unmatched)} keys not present in raw file, e.g. {sample}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate experiment JSONL outputs")
    parser.add_argument("--raw", type=Path, required=True, help="Raw generations JSONL")
    parser.add_argument("--tested", type=Path, required=True, help="Test results JSONL")
    parser.add_argument("--expected-tasks", type=int, required=True)
    parser.add_argument("--expected-conditions", type=int, required=True)
    parser.add_argument("--expected-samples", type=int, required=True)
    parser.add_argument("--expected-strategy", type=str, default="standard", help="Expected strategy value (default: standard)")
    args = parser.parse_args()

    raw_records = load_jsonl(args.raw)
    expected_tasks = {r["task_id"] for r in raw_records}
    expected_conditions = {r["condition"] for r in raw_records}

    # If counts are provided, they must match observed unique counts.
    if len(expected_tasks) != args.expected_tasks:
        print(f"ERROR: expected {args.expected_tasks} tasks, found {len(expected_tasks)}")
        return 1
    if len(expected_conditions) != args.expected_conditions:
        print(f"ERROR: expected {args.expected_conditions} conditions, found {len(expected_conditions)}")
        return 1
    if args.expected_samples < 1:
        print("ERROR: expected-samples must be >= 1")
        return 1

    errors: list[str] = []
    errors.extend(validate_raw(args.raw, expected_tasks, expected_conditions, args.expected_samples, args.expected_strategy))
    errors.extend(validate_tested(args.tested, raw_records, expected_tasks, expected_conditions, args.expected_samples, args.expected_strategy))

    if errors:
        print(f"FAILED: {len(errors)} issue(s)")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("OK: all validation checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
