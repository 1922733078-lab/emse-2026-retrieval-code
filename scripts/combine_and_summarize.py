"""Combine metrics from multiple models and generate publication-ready tables/figures."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
TABLES_DIR = RESULTS_DIR / "tables"
FIGURES_DIR = RESULTS_DIR / "figures"
TABLES_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME_MAP = {
    "gpt-5.5": "GPT-5.5",
    "deepseek-v4-flash": "DeepSeek-V4-Flash",
    "Qwen2.5-Coder-7B-Instruct": "Qwen2.5-Coder-7B",
    "Qwen2.5-Coder-14B-Instruct": "Qwen2.5-Coder-14B",
    "Qwen2.5-Coder-3B-Instruct": "Qwen2.5-Coder-3B",
    "Qwen2___5-Coder-7B-Instruct": "Qwen2.5-Coder-7B",
    "Qwen2___5-Coder-3B-Instruct": "Qwen2.5-Coder-3B",
    "reference_oracle": "Reference Oracle",
    "codellama-7b-instruct.Q5_K_M.gguf": "CodeLlama-7B",
    "LongCat-2.0": "LongCat-2.0",
    "longcat_2_0": "LongCat-2.0",
    "MiniMax-M2.5": "MiniMax-M2.5",
    "minimax_m25": "MiniMax-M2.5",
}


def normalize_model(name: str) -> str:
    if name in MODEL_NAME_MAP:
        return MODEL_NAME_MAP[name]
    # Handle ModelScope cache paths that end with the model dir name.
    for key, mapped in MODEL_NAME_MAP.items():
        if name.endswith(key):
            return mapped
    return name


def load_metrics(path: Path) -> pd.DataFrame:
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            rec["model"] = normalize_model(rec["model"])
            records.append(rec)
    df = pd.DataFrame(records)
    df["level"] = df["task_id"].apply(
        lambda tid: "L1" if "_l1_" in tid else ("L2" if "_l2_" in tid else "L3")
    )
    return df


def compute_pass_at_1(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["model", "level", "condition"])
        .agg(pass_at_1=("passed", "mean"), n=("passed", "count"))
        .reset_index()
    )
    grouped["pass_at_1_pct"] = grouped["pass_at_1"] * 100
    return grouped


def compute_retrieval_effects(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, level), group in df.groupby(["model", "level"]):
        by_cond = group.groupby("condition")["passed"].mean().to_dict()
        rows.append(
            {
                "model": model,
                "level": level,
                "retrieval_gain": by_cond.get("gold", 0) - by_cond.get("no", 0),
                "distractor_loss": by_cond.get("gold", 0) - by_cond.get("distractor", 0),
                "misleading_effect": by_cond.get("no", 0) - by_cond.get("distractor", 0),
            }
        )
    return pd.DataFrame(rows)


def save_main_table(pass_df: pd.DataFrame, suffix: str = "") -> None:
    pivot = pass_df.pivot_table(
        index=["model", "level"],
        columns="condition",
        values="pass_at_1_pct",
        aggfunc="first",
    ).reset_index()
    order = ["no", "naive", "gold", "distractor"]
    pivot = pivot[["model", "level"] + [c for c in order if c in pivot.columns]]
    pivot_path = TABLES_DIR / f"pass_at_1{suffix}.csv"
    pivot.to_csv(pivot_path, index=False, float_format="%.1f")
    print(f"Saved Pass@1 table to {pivot_path}")


def save_effects_table(effects_df: pd.DataFrame, suffix: str = "") -> None:
    effects_df[["retrieval_gain", "distractor_loss", "misleading_effect"]] *= 100
    path = TABLES_DIR / f"retrieval_effects{suffix}.csv"
    effects_df.to_csv(path, index=False, float_format="%.1f")
    print(f"Saved retrieval effects table to {path}")


def plot_pass_at_1(pass_df: pd.DataFrame, suffix: str = "") -> None:
    sns.set_style("whitegrid")
    g = sns.catplot(
        data=pass_df,
        x="condition",
        y="pass_at_1_pct",
        hue="level",
        col="model",
        kind="bar",
        height=4,
        aspect=1.2,
        order=[c for c in ["no", "naive", "gold", "distractor"] if c in pass_df["condition"].unique()],
        hue_order=["L1", "L2", "L3"],
        palette="viridis",
    )
    g.set_axis_labels("Retrieval Condition", "Pass@1 (%)")
    g.set_titles("{col_name}")
    g._legend.set_title("Level")
    plt.tight_layout()
    path = FIGURES_DIR / f"pass_at_1_by_condition{suffix}.png"
    plt.savefig(path, dpi=300)
    print(f"Saved figure to {path}")
    plt.close()


def plot_retrieval_effects(effects_df: pd.DataFrame, suffix: str = "") -> None:
    effects_melted = effects_df.melt(
        id_vars=["model", "level"],
        value_vars=["retrieval_gain", "distractor_loss", "misleading_effect"],
        var_name="metric",
        value_name="percentage_points",
    )
    sns.set_style("whitegrid")
    g = sns.catplot(
        data=effects_melted,
        x="level",
        y="percentage_points",
        hue="metric",
        col="model",
        kind="bar",
        height=4,
        aspect=1.2,
    )
    g.set_axis_labels("Level", "Percentage Points")
    g.set_titles("{col_name}")
    plt.tight_layout()
    path = FIGURES_DIR / f"retrieval_effects{suffix}.png"
    plt.savefig(path, dpi=300)
    print(f"Saved figure to {path}")
    plt.close()


def plot_similarity_vs_correctness(df: pd.DataFrame, suffix: str = "") -> None:
    df = df[df["condition"].isin(["gold", "distractor", "naive"])].copy()
    df["correct"] = df["passed"].astype(int)
    sns.set_style("whitegrid")
    g = sns.FacetGrid(df, col="condition", row="level", margin_titles=True, height=2.8)
    g.map_dataframe(sns.scatterplot, x="max_similarity_to_retrieval", y="correct", alpha=0.6, hue="model")
    g.set_axis_labels("Max Similarity to Retrieval", "Correct")
    plt.tight_layout()
    path = FIGURES_DIR / f"similarity_vs_correctness{suffix}.png"
    plt.savefig(path, dpi=300)
    print(f"Saved figure to {path}")
    plt.close()


def plot_error_distribution(df: pd.DataFrame, suffix: str = "") -> None:
    error_df = df[~df["passed"]].copy()
    if error_df.empty:
        return
    sns.set_style("whitegrid")
    g = sns.catplot(
        data=error_df,
        x="error_type",
        hue="condition",
        col="level",
        row="model",
        kind="count",
        height=3,
        aspect=1.8,
    )
    g.set_axis_labels("Error Type", "Count")
    g.set_titles("{col_name} | {row_name}")
    for ax in g.axes.flat:
        for label in ax.get_xticklabels():
            label.set_rotation(45)
            label.set_horizontalalignment("right")
    plt.tight_layout()
    path = FIGURES_DIR / f"error_distribution{suffix}.png"
    plt.savefig(path, dpi=300)
    print(f"Saved figure to {path}")
    plt.close()


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: combine_and_summarize.py <output_suffix> <metrics1.jsonl> [metrics2.jsonl ...]")
        sys.exit(1)

    suffix = sys.argv[1]
    if not suffix.startswith("_"):
        suffix = "_" + suffix

    dfs = [load_metrics(Path(p)) for p in sys.argv[2:]]
    df = pd.concat(dfs, ignore_index=True)

    pass_df = compute_pass_at_1(df)
    save_main_table(pass_df, suffix)

    effects_df = compute_retrieval_effects(df)
    save_effects_table(effects_df, suffix)

    plot_pass_at_1(pass_df, suffix)
    plot_retrieval_effects(effects_df, suffix)
    plot_similarity_vs_correctness(df, suffix)
    plot_error_distribution(df, suffix)

    print("Combined summary complete.")


if __name__ == "__main__":
    main()
