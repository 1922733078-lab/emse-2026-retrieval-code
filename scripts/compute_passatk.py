"""Compute Pass@k from test results for multi-sample generation experiments.

Reads a JSONL file of test results (possibly containing multiple sample_ids
per task) and computes Pass@1, Pass@2, Pass@3 aggregated by model and
condition. Optionally also breaks down by difficulty level (L1/L2/L3).
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def compute_passatk(passed: list[int], k: int) -> float:
    """Compute empirical Pass@k for a list of binary pass indicators."""
    if not passed:
        return 0.0
    k = min(k, len(passed))
    # Probability that at least one of the first k samples passes.
    failures = [1 - p for p in passed[:k]]
    prod = 1.0
    for f in failures:
        prod *= f
    return 1.0 - prod


def load_results(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    return records


def difficulty(task_id: str) -> str:
    if "_l1_" in task_id:
        return "L1"
    if "_l2_" in task_id:
        return "L2"
    if "_l3_" in task_id:
        return "L3"
    return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="+", type=Path, help="Test results JSONL file(s)")
    parser.add_argument("--output", type=Path, help="Output CSV file (default: stdout)")
    parser.add_argument("--max-k", type=int, default=3, help="Maximum k for Pass@k")
    parser.add_argument("--by-level", action="store_true", help="Also report breakdown by L1/L2/L3")
    args = parser.parse_args()

    records: list[dict[str, Any]] = []
    for path in args.input:
        records.extend(load_results(path))

    # Group by (model, condition, task_id) -> ordered list of pass indicators by sample_id.
    groups: dict[tuple[str, str, str], dict[int, int]] = defaultdict(dict)
    for r in records:
        model = r.get("model", "unknown")
        condition = r.get("condition", "unknown")
        task_id = r["task_id"]
        sample_id = r.get("sample_id", 0)
        passed = 1 if r.get("passed", False) else 0
        groups[(model, condition, task_id)][sample_id] = passed

    # Aggregate overall.
    overall: dict[tuple[str, str], list[list[int]]] = defaultdict(list)
    by_level: dict[tuple[str, str, str], list[list[int]]] = defaultdict(list)

    for (model, condition, task_id), sample_map in groups.items():
        max_sample = max(sample_map.keys())
        passes = [sample_map.get(i, 0) for i in range(max_sample + 1)]
        overall[(model, condition)].append(passes)
        if args.by_level:
            lvl = difficulty(task_id)
            by_level[(model, condition, lvl)].append(passes)

    # Build rows.
    rows = []
    for (model, condition), task_passes in sorted(overall.items()):
        row = {"model": model, "condition": condition, "level": "All", "n_tasks": len(task_passes)}
        for k in range(1, args.max_k + 1):
            passatk = sum(compute_passatk(tp, k) for tp in task_passes) / len(task_passes)
            row[f"pass@{k}"] = round(passatk * 100, 2)
        rows.append(row)

    if args.by_level:
        for (model, condition, lvl), task_passes in sorted(by_level.items()):
            row = {"model": model, "condition": condition, "level": lvl, "n_tasks": len(task_passes)}
            for k in range(1, args.max_k + 1):
                passatk = sum(compute_passatk(tp, k) for tp in task_passes) / len(task_passes)
                row[f"pass@{k}"] = round(passatk * 100, 2)
            rows.append(row)

    # Write CSV.
    import csv
    import sys

    fieldnames = ["model", "condition", "level", "n_tasks"]
    for k in range(1, args.max_k + 1):
        fieldnames.append(f"pass@{k}")
    # Keep only fields that actually appear in any row.
    if rows:
        fieldnames = [fn for fn in fieldnames if any(fn in row for row in rows)]
    output_stream = args.output.open("w", encoding="utf-8", newline="") if args.output else sys.stdout
    writer = csv.DictWriter(output_stream, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    if args.output:
        output_stream.close()
        print(f"Wrote Pass@k results to {args.output}")


if __name__ == "__main__":
    main()
