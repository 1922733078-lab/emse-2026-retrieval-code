"""Generate supplementary experiment tables for the paper.

Produces:
- Table X: CoT ablation (standard vs CoT Pass@1)
- Table Y: Pass@k results (Pass@1/2/3)
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_results(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    return records


def normalize_model(name: str) -> str:
    """Map raw model identifiers to display names."""
    name_lower = name.lower()
    if "qwen" in name_lower and "3b" in name_lower:
        return "Qwen2.5-Coder-3B-Instruct"
    if "qwen" in name_lower and "7b" in name_lower:
        return "Qwen2.5-Coder-7B-Instruct"
    if "codellama" in name_lower:
        return "CodeLlama-7B-Instruct-Q5_K_M"
    if "deepseek" in name_lower:
        return "deepseek-v4-flash"
    if "longcat" in name_lower:
        return "LongCat-2.0"
    if "minimax" in name_lower:
        return "MiniMax-M2.5"
    return name


def pass_at_1(records: list[dict[str, Any]]) -> dict[tuple[str, str], float]:
    """Return Pass@1 per (model, condition)."""
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for r in records:
        model = normalize_model(r.get("model", "unknown"))
        condition = r.get("condition", "unknown")
        passed = 1 if r.get("passed", False) else 0
        groups[(model, condition)].append(passed)
    return {key: sum(vals) / len(vals) * 100 for key, vals in groups.items()}


def compute_passatk(records: list[dict[str, Any]], max_k: int = 3) -> dict[tuple[str, str, str], dict[int, float]]:
    """Return Pass@k per (model, condition, level). level='All' for overall."""
    # Group by (model, condition, task_id) -> sample passes.
    task_groups: dict[tuple[str, str, str], dict[int, int]] = defaultdict(dict)
    for r in records:
        model = normalize_model(r.get("model", "unknown"))
        condition = r.get("condition", "unknown")
        task_id = r["task_id"]
        sample_id = r.get("sample_id", 0)
        passed = 1 if r.get("passed", False) else 0
        task_groups[(model, condition, task_id)][sample_id] = passed

    def level(task_id: str) -> str:
        if "_l1_" in task_id:
            return "L1"
        if "_l2_" in task_id:
            return "L2"
        if "_l3_" in task_id:
            return "L3"
        return "unknown"

    # Overall and by-level groups.
    overall: dict[tuple[str, str], list[list[int]]] = defaultdict(list)
    by_level: dict[tuple[str, str, str], list[list[int]]] = defaultdict(list)
    for (model, condition, task_id), sample_map in task_groups.items():
        passes = [sample_map.get(i, 0) for i in range(max(sample_map.keys()) + 1)]
        overall[(model, condition)].append(passes)
        by_level[(model, condition, level(task_id))].append(passes)

    result: dict[tuple[str, str, str], dict[int, float]] = {}
    for (model, condition), task_passes in overall.items():
        result[(model, condition, "All")] = {
            k: sum(1 - math.prod([1 - p for p in tp[:k]]) for tp in task_passes) / len(task_passes) * 100
            for k in range(1, max_k + 1)
        }
    for (model, condition, lvl), task_passes in by_level.items():
        result[(model, condition, lvl)] = {
            k: sum(1 - math.prod([1 - p for p in tp[:k]]) for tp in task_passes) / len(task_passes) * 100
            for k in range(1, max_k + 1)
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("test_results_dir", type=Path, help="Directory containing test result JSONL files")
    parser.add_argument("output_dir", type=Path, help="Directory to write output CSV tables")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # Table X: CoT ablation.
    # Standard results come from existing files; CoT from p0 outputs.
    # -----------------------------------------------------------------------
    std_files = {
        "Qwen2.5-Coder-3B-Instruct": ["qwen_3b_results.jsonl"],
        "Qwen2.5-Coder-7B-Instruct": ["qwen_7b_results.jsonl"],
        "CodeLlama-7B-Instruct-Q5_K_M": ["codellama_7b_instruct_q5_k_m_results.jsonl"],
        "deepseek-v4-flash": [
            "deepseek_v4_flash_no_results.jsonl",
            "deepseek_v4_flash_naive_results.jsonl",
            "deepseek_v4_flash_gold_results.jsonl",
            "deepseek_v4_flash_distractor_results.jsonl",
        ],
        "LongCat-2.0": [
            "longcat_2_0_main_results.jsonl",
        ],
    }
    cot_files = {
        "Qwen2.5-Coder-3B-Instruct": ["p0_qwen3b_cot_results.jsonl"],
        "Qwen2.5-Coder-7B-Instruct": ["p0_qwen7b_cot_results.jsonl"],
        "CodeLlama-7B-Instruct-Q5_K_M": ["p0_codellama_cot_results.jsonl"],
        "deepseek-v4-flash": ["p0_deepseek_v4_flash_cot_results.jsonl"],
        "LongCat-2.0": ["p0_longcat_2_0_cot_results.jsonl"],
    }

    # Collect standard Pass@1.
    std_pass1: dict[tuple[str, str], float] = {}
    for model, files in std_files.items():
        records = []
        for fn in files:
            path = args.test_results_dir / fn
            if path.exists():
                records.extend(load_results(path))
        std_pass1.update(pass_at_1(records))

    # Collect CoT Pass@1.
    cot_pass1: dict[tuple[str, str], float] = {}
    for model, files in cot_files.items():
        records = []
        for fn in files:
            path = args.test_results_dir / fn
            if path.exists():
                records.extend(load_results(path))
        cot_pass1.update(pass_at_1(records))

    # Build Table X.
    table_x_path = args.output_dir / "table_x_cot_ablation.csv"
    with table_x_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["model", "condition", "standard_pass@1", "cot_pass@1", "delta"])
        # GPT-5.5 and MiniMax-M2.5 are retained only as audit data and
        # deliberately excluded from the final five-model study.
        models = ["Qwen2.5-Coder-3B-Instruct", "Qwen2.5-Coder-7B-Instruct", "CodeLlama-7B-Instruct-Q5_K_M", "deepseek-v4-flash", "LongCat-2.0"]
        conditions = ["no", "gold", "distractor"]
        for model in models:
            for condition in conditions:
                std = std_pass1.get((model, condition))
                cot = cot_pass1.get((model, condition))
                row = [model, condition]
                row.append(f"{std:.2f}" if std is not None else "")
                row.append(f"{cot:.2f}" if cot is not None else "")
                if std is not None and cot is not None:
                    row.append(f"{cot - std:+.2f}")
                else:
                    row.append("")
                writer.writerow(row)
    print(f"Wrote Table X to {table_x_path}")

    # -----------------------------------------------------------------------
    # Table Y: Pass@k.
    # -----------------------------------------------------------------------
    passk_files = {
        "Qwen2.5-Coder-3B-Instruct": ["p1_qwen3b_n3_results.jsonl"],
        "Qwen2.5-Coder-7B-Instruct": ["p1_qwen7b_n3_results.jsonl"],
        "CodeLlama-7B-Instruct-Q5_K_M": ["p1_codellama_n3_results.jsonl"],
        "deepseek-v4-flash": ["p1_deepseek_v4_flash_n3_results.jsonl"],
        "LongCat-2.0": ["p1_longcat_2_0_n3_results.jsonl"],
    }

    passk_results: dict[tuple[str, str, str], dict[int, float]] = {}
    for model, files in passk_files.items():
        records = []
        for fn in files:
            path = args.test_results_dir / fn
            if path.exists():
                records.extend(load_results(path))
        if records:
            passk_results.update(compute_passatk(records, max_k=3))

    table_y_path = args.output_dir / "table_y_passatk.csv"
    with table_y_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["model", "condition", "level", "pass@1", "pass@2", "pass@3"])
        for (model, condition, lvl), vals in sorted(passk_results.items()):
            writer.writerow([
                model,
                condition,
                lvl,
                f"{vals[1]:.2f}",
                f"{vals[2]:.2f}",
                f"{vals[3]:.2f}",
            ])
    print(f"Wrote Table Y to {table_y_path}")


if __name__ == "__main__":
    main()
