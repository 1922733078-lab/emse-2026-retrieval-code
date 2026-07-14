"""Compute paired statistical tests for retrieval conditions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results" / "tables"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME_MAP = {
    "gpt-5.5": "GPT-5.5",
    "deepseek-v4-flash": "DeepSeek-V4-Flash",
    "Qwen2.5-Coder-7B-Instruct": "Qwen2.5-Coder-7B",
    "Qwen2.5-Coder-14B-Instruct": "Qwen2.5-Coder-14B",
    "Qwen2.5-Coder-3B-Instruct": "Qwen2.5-Coder-3B",
    "Qwen2___5-Coder-7B-Instruct": "Qwen2.5-Coder-7B",
    "Qwen2___5-Coder-3B-Instruct": "Qwen2.5-Coder-3B",
    "reference_oracle": "Reference Oracle",
    "codellama-7b-instruct.Q5_K_M.gguf": "CodeLlama-7B-Instruct-Q5_K_M",
    "LongCat-2.0": "LongCat-2.0",
    "longcat_2_0": "LongCat-2.0",
    "MiniMax-M2.5": "MiniMax-M2.5",
    "minimax_m25": "MiniMax-M2.5",
}


def normalize_model(name: str) -> str:
    if name in MODEL_NAME_MAP:
        return MODEL_NAME_MAP[name]
    for key, mapped in MODEL_NAME_MAP.items():
        if name.endswith(key):
            return mapped
    return name


COMPARISONS = [
    ("no", "gold", "no_vs_gold"),
    ("gold", "distractor", "gold_vs_distractor"),
    ("no", "distractor", "no_vs_distractor"),
]


def load_metrics(paths: list[Path]) -> pd.DataFrame:
    records = []
    for p in paths:
        with p.open(encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                rec["level"] = (
                    "L1" if "_l1_" in rec["task_id"] else
                    "L2" if "_l2_" in rec["task_id"] else "L3"
                )
                rec["model"] = normalize_model(rec.get("model", ""))
                records.append(rec)
    df = pd.DataFrame(records)
    df["passed"] = df["passed"].astype(bool)
    return df


def mcnemar_test(a_correct: np.ndarray, b_correct: np.ndarray) -> dict[str, Any]:
    """McNemar's test for paired proportions using exact binomial test."""
    n = len(a_correct)
    both = int(np.sum(a_correct & b_correct))
    a_only = int(np.sum(a_correct & ~b_correct))
    b_only = int(np.sum(~a_correct & b_correct))
    neither = int(np.sum(~a_correct & ~b_correct))
    discordant = a_only + b_only
    if discordant == 0:
        p_value = 1.0
        or_conditional = np.nan
    else:
        p_value = stats.binomtest(a_only, n=discordant, p=0.5, alternative="two-sided").pvalue
        or_conditional = (a_only / b_only) if b_only > 0 else np.inf
    return {
        "n": n,
        "both_correct": both,
        "a_only": a_only,
        "b_only": b_only,
        "neither_correct": neither,
        "discordant": discordant,
        "p_value": p_value,
        "conditional_or": or_conditional,
    }


def cohen_h(p1: float, p2: float) -> float:
    """Cohen's h for difference in proportions."""
    return 2 * (np.arcsin(np.sqrt(p1)) - np.arcsin(np.sqrt(p2)))


def bootstrap_diff_ci(a_correct: np.ndarray, b_correct: np.ndarray, n_boot: int = 10000, ci: float = 0.95) -> tuple[float, float]:
    """Bootstrap CI for the difference in paired proportions (b - a)."""
    diffs = b_correct.astype(float) - a_correct.astype(float)
    rng = np.random.default_rng(0)
    boot_means = []
    for _ in range(n_boot):
        sample = rng.choice(diffs, size=len(diffs), replace=True)
        boot_means.append(sample.mean())
    boot_means = np.array(boot_means)
    lower = np.percentile(boot_means, (1 - ci) / 2 * 100)
    upper = np.percentile(boot_means, (1 + ci) / 2 * 100)
    return float(lower), float(upper)


def compute_tests(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    models = sorted(df["model"].unique())
    levels = ["L1", "L2", "L3", "All"]
    for model in models:
        for level in levels:
            sub = df[df["model"] == model]
            if level != "All":
                sub = sub[sub["level"] == level]
            if sub.empty:
                continue
            for cond_a, cond_b, comp_name in COMPARISONS:
                a = sub[sub["condition"] == cond_a]
                b = sub[sub["condition"] == cond_b]
                merged = pd.merge(a[["task_id", "passed"]], b[["task_id", "passed"]], on="task_id", suffixes=("_a", "_b"))
                if len(merged) < 5:
                    continue
                a_correct = merged["passed_a"].values
                b_correct = merged["passed_b"].values
                mcnemar = mcnemar_test(a_correct, b_correct)
                p_a = a_correct.mean()
                p_b = b_correct.mean()
                diff = p_b - p_a
                ci_low, ci_high = bootstrap_diff_ci(a_correct, b_correct)
                h = cohen_h(p_b, p_a)
                rows.append({
                    "model": model,
                    "level": level,
                    "comparison": comp_name,
                    "n_tasks": len(merged),
                    "pass_rate_a": round(p_a * 100, 2),
                    "pass_rate_b": round(p_b * 100, 2),
                    "diff_pp": round(diff * 100, 2),
                    "ci_low_95": round(ci_low * 100, 2),
                    "ci_high_95": round(ci_high * 100, 2),
                    "mcnemar_p": mcnemar["p_value"],
                    "conditional_or": mcnemar["conditional_or"],
                    "cohens_h": round(h, 3),
                    "discordant_pairs": mcnemar["discordant"],
                })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("metrics", nargs="+", help="Path(s) to metrics JSONL files")
    parser.add_argument("--output", default=str(RESULTS_DIR / "statistical_tests.csv"))
    args = parser.parse_args()

    df = load_metrics([Path(p) for p in args.metrics])
    results = compute_tests(df)
    results = results.sort_values(["model", "level", "comparison"])
    results.to_csv(args.output, index=False, float_format="%.4g")
    print(f"Wrote statistical test results to {args.output}")
    # Print a concise summary.
    sig = results[results["mcnemar_p"] < 0.05]
    print(f"{len(sig)} of {len(results)} comparisons significant at p < 0.05")


if __name__ == "__main__":
    main()
