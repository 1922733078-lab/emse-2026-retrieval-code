"""Evaluate the quality of naive (BM25) retrieval against gold snippets."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def extract_function_names(snippets: list[str]) -> list[str]:
    names = []
    for s in snippets:
        m = re.search(r"^def\s+(\w+)\s*\(", s, re.MULTILINE)
        if m:
            names.append(m.group(1))
    return names


def evaluate() -> None:
    gold: dict[str, list[str]] = {}
    naive: dict[str, list[str]] = {}
    for lib in ("fluxon", "quorix", "nimbla"):
        with (ROOT / "retrieval_contexts" / "gold" / f"{lib}.json").open(encoding="utf-8") as f:
            gold.update(json.load(f))
        with (ROOT / "retrieval_contexts" / "naive" / f"{lib}.json").open(encoding="utf-8") as f:
            naive.update(json.load(f))

    total = len(gold)
    recall_at_5 = 0.0
    reciprocal_ranks = []
    exact_match_tasks = 0

    results = []
    for task_id, gold_snippets in gold.items():
        gold_names = set(extract_function_names(gold_snippets))
        naive_names = extract_function_names(naive.get(task_id, []))
        retrieved_set = set(naive_names)
        hits = len(gold_names & retrieved_set)
        recall_at_5 += hits / len(gold_names) if gold_names else 0

        rr = 0.0
        for rank, name in enumerate(naive_names, start=1):
            if name in gold_names:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

        if gold_names.issubset(retrieved_set):
            exact_match_tasks += 1

        results.append({
            "task_id": task_id,
            "gold_functions": sorted(gold_names),
            "naive_functions": naive_names,
            "recall": round(hits / len(gold_names) if gold_names else 0, 3),
            "mrr": round(rr, 3),
        })

    print(f"Tasks evaluated: {total}")
    print(f"Mean Recall@5: {recall_at_5 / total:.3f}")
    print(f"Mean MRR: {sum(reciprocal_ranks) / total:.3f}")
    print(f"Exact match tasks: {exact_match_tasks} ({exact_match_tasks / total * 100:.1f}%)")

    out_path = ROOT / "results" / "tables" / "naive_retrieval_quality.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump({
            "mean_recall_at_5": recall_at_5 / total,
            "mean_mrr": sum(reciprocal_ranks) / total,
            "exact_match_rate": exact_match_tasks / total,
            "per_task": results,
        }, f, indent=2, ensure_ascii=False)
    print(f"Wrote per-task quality metrics to {out_path}")


if __name__ == "__main__":
    evaluate()
