#!/usr/bin/env python3
"""Rebuild the two monochrome submission figures from the candidate Pass@1 CSV.

Adapted from 01-论文文稿/EMSE投稿稿/scripts/build_submission_figures.py.
Inputs and outputs are parameterized via CLI flags.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

MODELS = [
    "Qwen2.5-Coder-3B",
    "Qwen2.5-Coder-7B",
    "CodeLlama-7B",
    "DeepSeek-V4-Flash",
    "LongCat-2.0",
]
LEVELS = ["L1", "L2", "L3"]
CONDITIONS = ["no", "naive", "gold", "distractor"]
CONDITION_LABELS = {
    "no": "No retrieval",
    "naive": "Naive BM25",
    "gold": "Gold retrieval",
    "distractor": "Plausible distractor",
}
FACE = {"no": "#FFFFFF", "naive": "#D9D9D9", "gold": "#737373", "distractor": "#FFFFFF"}
HATCH = {"no": "", "naive": "///", "gold": "", "distractor": "xx"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def configure() -> None:
    mpl.rcParams.update(
        {
            "font.family": "Times New Roman",
            "font.size": 10,
            "axes.labelsize": 10,
            "axes.titlesize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.linewidth": 0.8,
        }
    )


def save(fig: plt.Figure, stem: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / f"{stem}.png", dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(out_dir / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def condition_figure(rows: list[dict[str, str]], out_dir: Path) -> None:
    values = {(row["model"], row["level"]): row for row in rows}
    fig, ax = plt.subplots(figsize=(4.62, 5.55))
    bar_h, gap = 0.16, 0.34
    centers, labels, y = [], [], 0.0
    for model in MODELS:
        first = y
        for level in LEVELS:
            row = values[(model, level)]
            for offset, condition in zip((1.5, 0.5, -0.5, -1.5), CONDITIONS):
                ax.barh(
                    y + offset * bar_h,
                    float(row[condition]),
                    height=bar_h,
                    color=FACE[condition],
                    edgecolor="black",
                    linewidth=0.7,
                    hatch=HATCH[condition],
                    zorder=3,
                )
            y += 1.0
        centers.append((first + y - 1.0) / 2)
        labels.append(model)
        y += gap

    ax.set_yticks(centers, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xticks(range(0, 101, 20))
    ax.set_xlabel("Pass@1 (%)")
    ax.xaxis.grid(True, color="#BFBFBF", linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, pad=4)
    ax.spines[["top", "right", "left"]].set_visible(False)
    handles = [
        Patch(facecolor=FACE[c], edgecolor="black", linewidth=0.7, hatch=HATCH[c],
              label=CONDITION_LABELS[c])
        for c in CONDITIONS
    ]
    ax.legend(handles=handles, ncol=2, loc="lower center", bbox_to_anchor=(0.5, 1.01),
              columnspacing=1.1, handlelength=1.3, frameon=False)
    ax.text(0.0, -0.085, "Within each model, bars are L1 (top), L2, and L3 (bottom).",
            transform=ax.transAxes, fontsize=10, va="top")
    fig.subplots_adjust(left=0.36, right=0.98, top=0.89, bottom=0.10)
    save(fig, "figure_1_monochrome_conditions", out_dir)


def paired_figure(rows: list[dict[str, str]], out_dir: Path) -> None:
    values = {(row["model"], row["level"]): row for row in rows}
    fig, ax = plt.subplots(figsize=(4.62, 5.35))
    y_positions, labels, y = [], [], 0.0
    for model in MODELS:
        for level in LEVELS:
            row = values[(model, level)]
            distractor = float(row["distractor"])
            gold = float(row["gold"])
            ax.plot([distractor, gold], [y, y], color="#737373", linewidth=1.4, zorder=2)
            ax.scatter(distractor, y, marker="o", s=36, facecolors="white",
                       edgecolors="black", linewidths=0.9, zorder=3)
            ax.scatter(gold, y, marker="s", s=34, facecolors="black",
                       edgecolors="black", linewidths=0.8, zorder=3)
            y_positions.append(y)
            labels.append(f"{model} · {level}")
            y += 1.0
        y += 0.26

    ax.set_yticks(y_positions, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xticks(range(0, 101, 20))
    ax.set_xlabel("Pass@1 (%)")
    ax.xaxis.grid(True, color="#BFBFBF", linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, pad=4)
    ax.spines[["top", "right", "left"]].set_visible(False)
    handles = [
        plt.Line2D([0], [0], marker="s", color="black", markerfacecolor="black",
                   markersize=6, linewidth=0, label="Gold retrieval"),
        plt.Line2D([0], [0], marker="o", color="black", markerfacecolor="white",
                   markersize=6, linewidth=0, label="Plausible distractor"),
    ]
    ax.legend(handles=handles, ncol=2, loc="lower center", bbox_to_anchor=(0.5, 1.01),
              columnspacing=1.4, handletextpad=0.5, frameon=False)
    fig.subplots_adjust(left=0.48, right=0.98, top=0.89, bottom=0.10)
    save(fig, "figure_2_monochrome_paired_effects", out_dir)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    csv_path = Path(args.input_csv)
    out_dir = Path(args.output_dir)
    if not csv_path.exists():
        print(f"Input CSV missing: {csv_path}", file=sys.stderr)
        return 2

    rows = read_csv(csv_path)
    if len(rows) != 15:
        print(f"FAIL: expected 15 rows, got {len(rows)}", file=sys.stderr)
        return 1
    for r in rows:
        if r["model"] not in MODELS:
            print(f"FAIL: unexpected model {r['model']}", file=sys.stderr)
            return 1

    configure()
    condition_figure(rows, out_dir)
    paired_figure(rows, out_dir)
    print(f"Wrote figures to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
