"""Build dense and hybrid retrieval contexts for E7 robustness experiment."""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import MinMaxScaler

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

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 5
HYBRID_ALPHA = 0.5  # weight for dense; BM25 gets (1-alpha)
RANDOM_SEED = 20260710


def get_public_functions(module) -> list[tuple[str, str]]:
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


def normalize_scores(scores: np.ndarray) -> np.ndarray:
    """Min-max normalize scores to [0, 1]."""
    if scores.max() == scores.min():
        return np.zeros_like(scores)
    return (scores - scores.min()) / (scores.max() - scores.min())


def build_dense_context(
    lib_name: str,
    task_ids: list[str],
    model: SentenceTransformer,
    top_k: int = TOP_K,
) -> dict[str, list[str]]:
    module = LIBRARIES[lib_name]
    functions = get_public_functions(module)
    corpus_sources = [src for _, src in functions]
    corpus_names = [name for name, _ in functions]

    print(f"[{lib_name}] Embedding {len(corpus_sources)} corpus functions...")
    corpus_embeddings = model.encode(corpus_sources, convert_to_numpy=True, show_progress_bar=False)

    context: dict[str, list[str]] = {}
    tasks_path = ROOT / "tasks" / f"{lib_name}_all.jsonl"
    with tasks_path.open(encoding="utf-8") as f:
        for line in f:
            task = json.loads(line)
            if task["task_id"] not in set(task_ids):
                continue
            query = f"{task['prompt']} {task['signature']}"
            query_embedding = model.encode(query, convert_to_numpy=True)
            sims = corpus_embeddings @ query_embedding
            top_indices = np.argsort(sims)[::-1][:top_k]
            snippets = [corpus_sources[i] for i in top_indices]
            context[task["task_id"]] = snippets
    return context


def build_hybrid_context(
    lib_name: str,
    task_ids: list[str],
    model: SentenceTransformer,
    top_k: int = TOP_K,
    alpha: float = HYBRID_ALPHA,
) -> dict[str, list[str]]:
    module = LIBRARIES[lib_name]
    functions = get_public_functions(module)
    corpus_sources = [src for _, src in functions]
    corpus_tokens = [src.split() for src in corpus_sources]
    bm25 = BM25Okapi(corpus_tokens)

    print(f"[{lib_name}] Embedding {len(corpus_sources)} corpus functions for hybrid...")
    corpus_embeddings = model.encode(corpus_sources, convert_to_numpy=True, show_progress_bar=False)

    context: dict[str, list[str]] = {}
    tasks_path = ROOT / "tasks" / f"{lib_name}_all.jsonl"
    with tasks_path.open(encoding="utf-8") as f:
        for line in f:
            task = json.loads(line)
            if task["task_id"] not in set(task_ids):
                continue
            query = f"{task['prompt']} {task['signature']}"
            query_tokens = query.split()
            bm25_scores = np.array(bm25.get_scores(query_tokens), dtype=np.float64)
            dense_scores = corpus_embeddings @ model.encode(query, convert_to_numpy=True)

            bm25_norm = normalize_scores(bm25_scores)
            dense_norm = normalize_scores(dense_scores)
            fused = alpha * dense_norm + (1 - alpha) * bm25_norm

            top_indices = np.argsort(fused)[::-1][:top_k]
            snippets = [corpus_sources[i] for i in top_indices]
            context[task["task_id"]] = snippets
    return context


def load_pilot_task_ids() -> list[str]:
    pilot_path = ROOT / "tasks" / "longcat_pilot_90.jsonl"
    ids = []
    with pilot_path.open(encoding="utf-8") as f:
        for line in f:
            task = json.loads(line)
            ids.append(task["task_id"])
    return ids


def main() -> None:
    np.random.seed(RANDOM_SEED)
    task_ids = load_pilot_task_ids()
    print(f"Building retrieval contexts for {len(task_ids)} pilot tasks")

    model = SentenceTransformer(EMBEDDING_MODEL)

    dense_dir = ROOT / "retrieval_contexts" / "dense"
    hybrid_dir = ROOT / "retrieval_contexts" / "hybrid"
    dense_dir.mkdir(parents=True, exist_ok=True)
    hybrid_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "embedding_model": EMBEDDING_MODEL,
        "top_k": TOP_K,
        "hybrid_alpha": HYBRID_ALPHA,
        "random_seed": RANDOM_SEED,
        "n_tasks": len(task_ids),
        "task_ids": task_ids,
    }

    for lib_name in LIBRARIES:
        dense_ctx = build_dense_context(lib_name, task_ids, model, TOP_K)
        out_path = dense_dir / f"{lib_name}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(dense_ctx, f, ensure_ascii=False, indent=2)
        print(f"Wrote {out_path} with {len(dense_ctx)} entries")

        hybrid_ctx = build_hybrid_context(lib_name, task_ids, model, TOP_K, HYBRID_ALPHA)
        out_path = hybrid_dir / f"{lib_name}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(hybrid_ctx, f, ensure_ascii=False, indent=2)
        print(f"Wrote {out_path} with {len(hybrid_ctx)} entries")

    manifest_path = ROOT / "retrieval_contexts" / "dense_hybrid_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"Wrote manifest to {manifest_path}")


if __name__ == "__main__":
    main()
