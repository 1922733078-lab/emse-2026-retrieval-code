"""Build naive (BM25) retrieval contexts for each library."""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "libs" / "fluxon"))
sys.path.insert(0, str(ROOT / "libs" / "quorix"))
sys.path.insert(0, str(ROOT / "libs" / "nimbla"))

import fluxon
import nimbla
import quorix

LIBRARIES = {
    "fluxon": fluxon,
    "quorix": quorix,
    "nimbla": nimbla,
}


def get_public_functions(module) -> list[tuple[str, str]]:
    """Return (name, source) for all public functions in a module."""
    functions = []
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if name.startswith("_"):
            continue
        try:
            source = inspect.getsource(obj)
        except (OSError, TypeError):
            continue
        functions.append((name, source))
    return functions


def build_naive_context(lib_name: str, top_k: int = 5) -> dict[str, list[str]]:
    module = LIBRARIES[lib_name]
    functions = get_public_functions(module)
    corpus_sources = [src for _, src in functions]
    corpus_tokens = [src.split() for src in corpus_sources]
    bm25 = BM25Okapi(corpus_tokens)

    context: dict[str, list[str]] = {}
    all_path = ROOT / "tasks" / f"{lib_name}_all.jsonl"
    with all_path.open(encoding="utf-8") as f:
        for line in f:
            task = json.loads(line)
            query = f"{task['prompt']} {task['signature']}"
            query_tokens = query.split()
            scores = bm25.get_scores(query_tokens)
            top_indices = sorted(
                range(len(scores)), key=lambda i: scores[i], reverse=True
            )[:top_k]
            snippets = [corpus_sources[i] for i in top_indices]
            context[task["task_id"]] = snippets
    return context


def main() -> None:
    output_dir = ROOT / "retrieval_contexts" / "naive"
    output_dir.mkdir(parents=True, exist_ok=True)
    for lib_name in LIBRARIES:
        context = build_naive_context(lib_name, top_k=5)
        out_path = output_dir / f"{lib_name}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(context, f, ensure_ascii=False, indent=2)
        print(f"Wrote {out_path} with {len(context)} entries")


if __name__ == "__main__":
    main()
