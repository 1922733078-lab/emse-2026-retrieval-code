#!/usr/bin/env python3
"""Rebuild the final-five-model Pass@1 table from frozen test results.

Reads the E1 main experiment test results for the five final models and
recomputes Pass@1 as the percentage of passed tasks per
model × level × condition. Output goes to --output-root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

CSV_COLUMNS = ["model", "level", "no", "naive", "gold", "distractor"]

MODEL_DISPLAY = {
    "qwen_3b": "Qwen2.5-Coder-3B",
    "qwen_7b": "Qwen2.5-Coder-7B",
    "codellama": "CodeLlama-7B",
    "deepseek_v4_flash": "DeepSeek-V4-Flash",
    "longcat_2_0": "LongCat-2.0",
}

MODEL_ORDER = [
    "codellama",
    "deepseek_v4_flash",
    "longcat_2_0",
    "qwen_3b",
    "qwen_7b",
]

CONDITIONS = ["no", "naive", "gold", "distractor"]
LEVELS = ["L1", "L2", "L3"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def level_from_task_id(task_id: str) -> str:
    parts = task_id.split("_")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse level from task_id: {task_id}")
    return parts[1].upper()


def compute_pass_at_1(test_path: Path) -> dict[tuple[str, str], dict[str, int]]:
    """Return {(level, condition): {pass, total}} from a test_results JSONL."""
    counts: dict[tuple[str, str], list[int]] = {}
    with test_path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            task_id = rec["task_id"]
            condition = rec["condition"]
            passed = rec.get("passed", False)
            if not isinstance(passed, bool):
                raise ValueError(
                    f"{test_path}:{line_no} 'passed' is not bool: {passed!r}"
                )
            level = level_from_task_id(task_id)
            key = (level, condition)
            if key not in counts:
                counts[key] = [0, 0]
            counts[key][1] += 1
            if passed:
                counts[key][0] += 1
    return counts


def validate_counts(counts: dict[tuple[str, str], list[int]], model_key: str) -> None:
    for level in LEVELS:
        for cond in CONDITIONS:
            key = (level, cond)
            if key not in counts:
                raise ValueError(
                    f"{model_key}: missing cell {level}/{cond}"
                )
            total = counts[key][1]
            if total != 150:
                raise ValueError(
                    f"{model_key}: {level}/{cond} has {total} tasks, expected 150"
                )


def write_csv(
    counts_by_model: dict[str, dict[tuple[str, str], list[int]]],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        f.write(",".join(CSV_COLUMNS) + "\n")
        for model_key in MODEL_ORDER:
            display = MODEL_DISPLAY[model_key]
            counts = counts_by_model[model_key]
            for level in LEVELS:
                values = []
                for cond in CONDITIONS:
                    p, t = counts[(level, cond)]
                    pct = round(p / t * 100, 1)
                    values.append(f"{pct:.1f}")
                f.write(",".join([display, level] + values) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--seed", type=int, default=20260713)
    args = parser.parse_args()

    artifact_root = Path(args.artifact_root).resolve()
    output_root = Path(args.output_root).resolve()

    with Path(args.manifest).open(encoding="utf-8") as f:
        manifest = json.load(f)

    models = manifest.get("models", {})
    experiments = manifest.get("experiments", {})
    e1 = experiments.get("E1_main", {})

    missing_raw = manifest.get("missing_raw_files", [])
    if missing_raw:
        print(f"FAIL: missing_raw_files is non-empty: {missing_raw}", file=sys.stderr)
        return 2

    counts_by_model: dict[str, dict[tuple[str, str], list[int]]] = {}
    input_files: list[dict[str, str]] = []

    for model_key in MODEL_ORDER:
        if model_key not in e1:
            raise ValueError(f"Model {model_key} not in E1_main")
        tested_path = e1[model_key]["tested"]
        full_path = artifact_root / tested_path
        if not full_path.exists():
            raise FileNotFoundError(f"tested file missing: {full_path}")
        file_sha = sha256_file(full_path)
        manifest_hash = e1[model_key].get("tested_sha256", "")
        if manifest_hash and file_sha != manifest_hash:
            raise ValueError(
                f"SHA mismatch for {tested_path}: {file_sha} != {manifest_hash}"
            )
        counts = compute_pass_at_1(full_path)
        validate_counts(counts, model_key)
        counts_by_model[model_key] = counts
        input_files.append({
            "path": str(tested_path),
            "sha256": file_sha,
        })

    out_csv = output_root / "results" / "tables" / "pass_at_1_final_five.csv"
    write_csv(counts_by_model, out_csv)

    provenance = {
        "script": "scripts/rebuild_final_five_tables.py",
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "manifest": str(args.manifest),
        "manifest_sha256": sha256_file(Path(args.manifest)),
        "seed": args.seed,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_files": input_files,
        "model_order": MODEL_ORDER,
        "model_display": MODEL_DISPLAY,
        "output": str(out_csv),
        "output_sha256": sha256_file(out_csv),
    }
    prov_path = output_root / "results" / "tables" / "rebuild_provenance.json"
    prov_path.parent.mkdir(parents=True, exist_ok=True)
    with prov_path.open("w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2, ensure_ascii=False)

    print(f"Wrote {out_csv}")
    print(f"Provenance: {prov_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
