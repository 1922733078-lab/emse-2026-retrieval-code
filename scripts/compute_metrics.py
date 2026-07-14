"""Compute similarity, citation, and error metrics on test results."""

from __future__ import annotations

import ast
import difflib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _load_all_contexts(condition: str) -> dict[str, list[str]]:
    combined: dict[str, list[str]] = {}
    for lib in ("fluxon", "quorix", "nimbla"):
        path = ROOT / "retrieval_contexts" / condition / f"{lib}.json"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as f:
            combined.update(json.load(f))
    return combined


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]+", text)


def jaccard_similarity(a: str, b: str) -> float:
    tokens_a = set(tokenize(a))
    tokens_b = set(tokenize(b))
    if not tokens_a and not tokens_b:
        return 1.0
    inter = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(inter) / len(union)


def levenshtein_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def max_similarity(code: str, snippets: list[str]) -> float:
    if not snippets:
        return 0.0
    return max(levenshtein_similarity(code, s) for s in snippets)


def nearest_snippet_distance(code: str, snippets: list[str]) -> float:
    if not snippets:
        return 1.0
    max_len = max(len(code), max(len(s) for s in snippets))
    if max_len == 0:
        return 0.0
    best = min(
        (len(code) + len(s) - 2 * len(difflib.SequenceMatcher(None, code, s).get_matching_blocks()) * 0.5)
        for s in snippets
    )
    # Use Levenshtein similarity inverse as normalized distance proxy.
    sim = max_similarity(code, snippets)
    return 1.0 - sim


def called_functions(code: str) -> set[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
    return names


def citation_rate(code: str, snippets: list[str]) -> float:
    calls = called_functions(code)
    if not calls:
        return 0.0
    snippet_calls: set[str] = set()
    for s in snippets:
        snippet_calls |= called_functions(s)
    if not snippet_calls:
        return 0.0
    return len(calls & snippet_calls) / len(calls)


# Conditions that reuse an existing context directory.
CONDITION_CONTEXT_MAP = {
    "distractor_reminder_mild": "distractor",
    "distractor_reminder_strong": "distractor",
    "gold_reminder_mild": "gold",
    "gold_reminder_strong": "gold",
}


def compute_for_record(record: dict[str, Any], contexts: dict[str, dict[str, list[str]]]) -> dict[str, Any]:
    condition = record["condition"]
    task_id = record["task_id"]
    code = record["generated_code"]

    ctx_key = CONDITION_CONTEXT_MAP.get(condition, condition)
    snippets = []
    if ctx_key in contexts:
        snippets = contexts[ctx_key].get(task_id, [])

    record["max_similarity_to_retrieval"] = max_similarity(code, snippets)
    record["edit_distance_to_nearest_snippet"] = nearest_snippet_distance(code, snippets)
    record["citation_rate"] = citation_rate(code, snippets)
    record["called_functions"] = sorted(called_functions(code))

    # More detailed error classification.
    if record.get("error_type") == "Assertion Error":
        # Try to detect copy-distractor patterns.
        if condition == "distractor" and record["max_similarity_to_retrieval"] > 0.5:
            record["error_type"] = "Copy Distractor"
        elif "_l3_" in record.get("task_id", ""):
            record["error_type"] = "Composition Error"
        else:
            record["error_type"] = "Boundary/Logic Error"

    return record


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: compute_metrics.py <input.jsonl> <output.jsonl>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    contexts = {
        "gold": _load_all_contexts("gold"),
        "distractor": _load_all_contexts("distractor"),
        "naive": _load_all_contexts("naive"),
    }

    with input_path.open(encoding="utf-8") as f_in, output_path.open(
        "w", encoding="utf-8"
    ) as f_out:
        for line in f_in:
            record = json.loads(line)
            record = compute_for_record(record, contexts)
            f_out.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote metrics to {output_path}")


if __name__ == "__main__":
    import re  # noqa: F401
    main()
