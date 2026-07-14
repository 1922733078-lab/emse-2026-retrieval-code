"""Clean statistical tests for the final five-model study.

Implements the requirements in the execution manual:
- paired McNemar exact test
- percentage-point difference and conditional odds ratio
- Cohen's h effect size
- paired bootstrap 95% CI
- Benjamini-Hochberg corrected p-values per comparison family
- raw exact p-values (no p=0.0000)
- stratification by model, level, and library
"""

from __future__ import annotations

import argparse
import json
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
    ("naive", "gold", "naive_vs_gold"),
]


def load_metrics(paths: list[Path]) -> pd.DataFrame:
    records = []
    for p in paths:
        with p.open(encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                tid = rec["task_id"]
                rec["level"] = "L1" if "_l1_" in tid else "L2" if "_l2_" in tid else "L3"
                rec["library"] = tid.split("_")[0]
                rec["model"] = normalize_model(rec.get("model", ""))
                records.append(rec)
    df = pd.DataFrame(records)
    df["passed"] = df["passed"].astype(bool)
    return df


def mcnemar_test(a_correct: np.ndarray, b_correct: np.ndarray) -> dict[str, Any]:
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
    return 2 * (np.arcsin(np.sqrt(p1)) - np.arcsin(np.sqrt(p2)))


def bootstrap_diff_ci(a_correct: np.ndarray, b_correct: np.ndarray, n_boot: int = 10000, ci: float = 0.95, seed: int = 0) -> tuple[float, float]:
    diffs = b_correct.astype(float) - a_correct.astype(float)
    rng = np.random.default_rng(seed)
    boot_means = np.empty(n_boot)
    for i in range(n_boot):
        sample = rng.choice(diffs, size=len(diffs), replace=True)
        boot_means[i] = sample.mean()
    lower = np.percentile(boot_means, (1 - ci) / 2 * 100)
    upper = np.percentile(boot_means, (1 + ci) / 2 * 100)
    return float(lower), float(upper)


def bh_correction(p_values: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg correction."""
    n = len(p_values)
    if n == 0:
        return p_values
    order = np.argsort(p_values)
    ranked = p_values[order]
    adjusted = np.empty(n)
    prev = 1.0
    for i in range(n - 1, -1, -1):
        raw = ranked[i] * n / (i + 1)
        raw = min(raw, prev)
        adjusted[order[i]] = raw
        prev = raw
    return adjusted


def compute_tests(df: pd.DataFrame, by_library: bool = False) -> pd.DataFrame:
    rows = []
    models = sorted(df["model"].unique())
    if by_library:
        groups = [("All", "All", "All")] + [(m, l, lib) for m in models for l in ["L1", "L2", "L3", "All"] for lib in sorted(df["library"].unique())]
    else:
        groups = [(m, l, "All") for m in models for l in ["L1", "L2", "L3", "All"]]

    for model, level, lib in groups:
        sub = df[df["model"] == model]
        if level != "All":
            sub = sub[sub["level"] == level]
        if lib != "All":
            sub = sub[sub["library"] == lib]
        if sub.empty:
            continue
        for cond_a, cond_b, comp_name in COMPARISONS:
            a = sub[sub["condition"] == cond_a]
            b = sub[sub["condition"] == cond_b]
            merged = pd.merge(
                a[["task_id", "passed"]],
                b[["task_id", "passed"]],
                on="task_id",
                suffixes=("_a", "_b"),
            )
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
                "library": lib,
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

    results = pd.DataFrame(rows)
    if results.empty:
        return results

    # BH correction within each (model, level, library) group across comparisons.
    results["p_bh"] = np.nan
    for _, grp in results.groupby(["model", "level", "library"]):
        idx = grp.index
        pvals = grp["mcnemar_p"].values
        results.loc[idx, "p_bh"] = bh_correction(pvals)

    results = results.sort_values(["model", "level", "library", "comparison"])
    return results


def format_p(p: float) -> str:
    if pd.isna(p):
        return ""
    if p < 0.001:
        return "<0.001"
    return f"{p:.4f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("metrics", nargs="+", help="Path(s) to metrics JSONL files")
    parser.add_argument("--output", default=str(RESULTS_DIR / "statistical_tests_clean.csv"))
    parser.add_argument("--by-library", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    df = load_metrics([Path(p) for p in args.metrics])
    results = compute_tests(df, by_library=args.by_library)
    if results.empty:
        print("No results to write")
        return

    # Format p-values for display.
    results["mcnemar_p_str"] = results["mcnemar_p"].apply(format_p)
    results["p_bh_str"] = results["p_bh"].apply(format_p)

    results.to_csv(args.output, index=False)
    print(f"Wrote statistical test results to {args.output}")
    sig = results[results["p_bh"] < 0.05]
    print(f"{len(sig)} of {len(results)} comparisons significant after BH correction at p < 0.05")


if __name__ == "__main__":
    main()
