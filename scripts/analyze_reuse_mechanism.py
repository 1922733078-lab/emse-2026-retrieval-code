"""Analyze code reuse mechanisms in retrieval-augmented generation.

This script implements the E6 reuse-mechanism analysis described in the
experiment manual.  For every generated solution it measures similarity to
retrieval snippets, gold snippets, distractor snippets, and reference
solutions, and classifies the solution into one of five reuse categories.

Thresholds are declared as module-level constants so they can be frozen after
the pilot human-coding phase.  They may be overridden via CLI arguments during
calibration, but the defaults registered here must not be tuned post-hoc to
improve agreement with outcomes.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import json
import re
import sys
import tempfile
import warnings
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent

RESULTS_DIR = ROOT / "results"
TABLES_DIR = RESULTS_DIR / "tables"
FIGURES_DIR = RESULTS_DIR / "figures"

RETRIEVAL_CONTEXTS_DIR = ROOT / "retrieval_contexts"
TASKS_FILE = ROOT / "tasks" / "all_tasks.jsonl"

# Pre-registered similarity thresholds.  These defaults are intended as
# starting values for the pilot human-coding phase; the final study should
# freeze them before applying the script to the full dataset.
DIRECT_REUSE_CHAR_THRESHOLD = 0.80
DIRECT_REUSE_TOKEN_THRESHOLD = 0.75
ADAPTED_REUSE_CHAR_THRESHOLD = 0.40
ADAPTED_REUSE_TOKEN_THRESHOLD = 0.35
ADAPTED_REUSE_MIN_FUNCTIONS_CALLED = 1
DISTRACTOR_SPECIFIC_MIN_MARKERS = 1

# Conditions that reuse an existing context directory.
CONDITION_CONTEXT_MAP: dict[str, str] = {
    "distractor_reminder_mild": "distractor",
    "distractor_reminder_strong": "distractor",
    "gold_reminder_mild": "gold",
    "gold_reminder_strong": "gold",
    "naive_topk_1": "naive_topk_1",
    "naive_topk_3": "naive_topk_3",
    "naive_topk_5": "naive_topk_5",
    "naive_topk_10": "naive_topk_10",
}

REUSE_CLASSES = [
    "direct_reuse",
    "adapted_reuse",
    "independent_solution",
    "distractor_error_inheritance",
    "invalid_unclassifiable",
]


def tokenize(text: str) -> list[str]:
    """Return alphanumeric tokens from ``text``."""
    return re.findall(r"[A-Za-z0-9_]+", text)


def token_jaccard(a: str, b: str) -> float:
    """Normalized token Jaccard similarity."""
    tokens_a = set(tokenize(a))
    tokens_b = set(tokenize(b))
    if not tokens_a and not tokens_b:
        return 1.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def char_similarity(a: str, b: str) -> float:
    """Character-level SequenceMatcher ratio."""
    return difflib.SequenceMatcher(None, a, b).ratio()


def nearest_distance(code: str, snippets: list[str]) -> float:
    """Normalized distance to the nearest snippet (1 - max char similarity)."""
    if not snippets:
        return 1.0
    return 1.0 - max(char_similarity(code, s) for s in snippets)


def parse_tree(code: str) -> ast.AST | None:
    """Parse ``code`` into an AST, returning ``None`` on failure."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            return ast.parse(code)
    except SyntaxError:
        return None


def ast_node_signature(tree: ast.AST) -> set[str]:
    """Return a set of AST node-type names, ignoring docstrings/literals."""
    return {type(node).__name__ for node in ast.walk(tree)}


def ast_call_names(tree: ast.AST) -> set[str]:
    """Return names/attributes called in ``tree``."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
    return names


def ast_function_definitions(tree: ast.AST) -> set[str]:
    """Return top-level function names defined in ``tree``."""
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and isinstance(node.parent, ast.Module)  # type: ignore[attr-defined]
    }


def _set_parents(tree: ast.AST) -> None:
    """Attach parent pointers so ``ast_function_definitions`` can filter roots."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node  # type: ignore[attr-defined]


def ast_similarity(a: str, b: str) -> dict[str, float]:
    """Compute AST node and call-structure Jaccard similarities.

    Returns a dict with keys ``node_jaccard`` and ``call_jaccard``.
    """
    tree_a = parse_tree(a)
    tree_b = parse_tree(b)
    if tree_a is None or tree_b is None:
        return {"node_jaccard": 0.0, "call_jaccard": 0.0}

    nodes_a = ast_node_signature(tree_a)
    nodes_b = ast_node_signature(tree_b)
    node_jaccard = (
        len(nodes_a & nodes_b) / len(nodes_a | nodes_b) if nodes_a | nodes_b else 1.0
    )

    calls_a = ast_call_names(tree_a)
    calls_b = ast_call_names(tree_b)
    call_jaccard = (
        len(calls_a & calls_b) / len(calls_a | calls_b) if calls_a | calls_b else 0.0
    )

    return {"node_jaccard": node_jaccard, "call_jaccard": call_jaccard}


def defined_functions(snippets: list[str]) -> set[str]:
    """Return all function names defined across ``snippets``."""
    names: set[str] = set()
    for s in snippets:
        tree = parse_tree(s)
        if tree is None:
            continue
        _set_parents(tree)
        names |= ast_function_definitions(tree)
    return names


def count_called_functions_from_snippets(code: str, snippets: list[str]) -> int:
    """Count how many functions defined in ``snippets`` are called by ``code``."""
    snippet_funcs = defined_functions(snippets)
    if not snippet_funcs:
        return 0
    tree = parse_tree(code)
    if tree is None:
        return 0
    calls = ast_call_names(tree)
    return len(calls & snippet_funcs)


def literal_markers(code: str) -> set[str]:
    """Extract string and numeric literals from ``code``."""
    tree = parse_tree(code)
    if tree is None:
        return set()
    markers: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            val = node.value
            if isinstance(val, (str, int, float, bool)):
                markers.add(repr(val))

    return markers


def distractor_specific_markers(
    gold_snippets: list[str], distractor_snippets: list[str]
) -> set[str]:
    """Return literals present in distractor snippets but not gold snippets."""
    gold_literals: set[str] = set()
    for s in gold_snippets:
        gold_literals |= literal_markers(s)

    distractor_literals: set[str] = set()
    for s in distractor_snippets:
        distractor_literals |= literal_markers(s)

    return distractor_literals - gold_literals


def distractor_function_markers(
    gold_snippets: list[str], distractor_snippets: list[str]
) -> set[str]:
    """Return function names defined in distractor but not gold snippets."""
    gold_funcs = defined_functions(gold_snippets)
    distractor_funcs = defined_functions(distractor_snippets)
    return distractor_funcs - gold_funcs


def inherited_distractor_markers(
    code: str,
    gold_snippets: list[str],
    distractor_snippets: list[str],
) -> dict[str, Any]:
    """Detect distractor-specific constants/branches/functions in ``code``."""
    literal_markers_set = distractor_specific_markers(gold_snippets, distractor_snippets)
    function_markers_set = distractor_function_markers(
        gold_snippets, distractor_snippets
    )

    code_literals = literal_markers(code)
    code_tree = parse_tree(code)
    code_calls = ast_call_names(code_tree) if code_tree else set()

    inherited_literals = code_literals & literal_markers_set
    inherited_functions = code_calls & function_markers_set

    return {
        "distractor_specific_literals": sorted(inherited_literals),
        "distractor_specific_functions": sorted(inherited_functions),
        "n_distractor_specific_markers": len(inherited_literals)
        + len(inherited_functions),
    }


def load_contexts(condition: str) -> dict[str, list[str]]:
    """Load retrieval snippets for ``condition`` across all libraries."""
    ctx_dir = RETRIEVAL_CONTEXTS_DIR / condition
    combined: dict[str, list[str]] = {}
    if not ctx_dir.exists():
        return combined
    for lib in ("fluxon", "quorix", "nimbla"):
        path = ctx_dir / f"{lib}.json"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                combined.update(data)
    return combined


def load_all_reference_contexts() -> dict[str, dict[str, list[str]]]:
    """Load gold/distractor/naive contexts for similarity comparisons."""
    return {
        "gold": load_contexts("gold"),
        "distractor": load_contexts("distractor"),
        "naive": load_contexts("naive"),
    }


def load_tasks(path: Path = TASKS_FILE) -> dict[str, dict[str, Any]]:
    """Load task definitions keyed by ``task_id``."""
    tasks: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return tasks
    with path.open(encoding="utf-8") as f:
        for line in f:
            task = json.loads(line)
            tasks[task["task_id"]] = task
    return tasks


def load_reference_solution(task: dict[str, Any]) -> str | None:
    """Load the reference solution for ``task`` if it exists."""
    ref_path = task.get("reference_solution_path")
    if not ref_path:
        return None
    abs_path = ROOT / ref_path
    if not abs_path.exists():
        return None
    try:
        return abs_path.read_text(encoding="utf-8")
    except OSError:
        return None


def record_key(record: dict[str, Any]) -> tuple[str, str, str, int]:
    """Return the matching key for a record."""
    return (
        record["task_id"],
        record["condition"],
        record.get("strategy", "standard"),
        record.get("sample_id", 0),
    )


def classify_reuse(
    condition: str,
    passed: bool,
    max_char_sim: float,
    max_token_jaccard: float,
    snippet_functions_called: int,
    n_distractor_markers: int,
    dist_to_distractor: float,
    dist_to_gold: float,
    thresholds: dict[str, float],
) -> str:
    """Classify a record into a reuse mechanism category.

    Classification follows a fixed priority order:
      1. invalid/unclassifiable (missing or unparseable code)
      2. direct_reuse (very high similarity to a retrieval snippet)
      3. distractor_error_inheritance (distractor condition, fails, and
         carries distractor-specific markers)
      4. adapted_reuse (moderate similarity or uses snippet functions)
      5. independent_solution (low similarity and no snippet reuse)
    """
    if not condition or max_char_sim < 0:
        return "invalid_unclassifiable"

    if (
        max_char_sim >= thresholds["direct_reuse_char"]
        or max_token_jaccard >= thresholds["direct_reuse_token"]
    ):
        return "direct_reuse"

    is_distractor = condition in {"distractor", "distractor_reminder_mild", "distractor_reminder_strong"}
    if (
        is_distractor
        and not passed
        and n_distractor_markers >= thresholds["distractor_min_markers"]
        and dist_to_distractor <= dist_to_gold + 0.05
    ):
        return "distractor_error_inheritance"

    if (
        max_char_sim >= thresholds["adapted_reuse_char"]
        or max_token_jaccard >= thresholds["adapted_reuse_token"]
        or snippet_functions_called >= thresholds["adapted_min_functions"]
    ):
        return "adapted_reuse"

    return "independent_solution"


def compute_record_features(
    record: dict[str, Any],
    contexts: dict[str, dict[str, list[str]]],
    tasks: dict[str, dict[str, Any]],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    """Compute all reuse features for a single matched record."""
    condition = record["condition"]
    task_id = record["task_id"]
    code = record.get("generated_code", "")
    passed = bool(record.get("passed", False))

    result: dict[str, Any] = {
        "task_id": task_id,
        "model": record.get("model_alias", record.get("model", "unknown")),
        "condition": condition,
        "strategy": record.get("strategy", "standard"),
        "sample_id": record.get("sample_id", 0),
        "passed": passed,
        "error_type": record.get("error_type"),
    }

    ctx_key = CONDITION_CONTEXT_MAP.get(condition, condition)
    snippets: list[str] = []
    if ctx_key in contexts:
        snippets = contexts[ctx_key].get(task_id, [])

    if not code.strip():
        result["reuse_class"] = "invalid_unclassifiable"
        result["invalid_reason"] = "empty_generated_code"
        return result

    # Similarity to retrieved snippets.
    char_sims = [char_similarity(code, s) for s in snippets]
    token_sims = [token_jaccard(code, s) for s in snippets]
    result["max_char_similarity"] = max(char_sims) if char_sims else 0.0
    result["max_token_jaccard"] = max(token_sims) if token_sims else 0.0
    result["mean_char_similarity"] = (
        sum(char_sims) / len(char_sims) if char_sims else 0.0
    )
    result["mean_token_jaccard"] = (
        sum(token_sims) / len(token_sims) if token_sims else 0.0
    )

    # AST-based similarities.
    ast_node_sims: list[float] = []
    ast_call_sims: list[float] = []
    for s in snippets:
        sims = ast_similarity(code, s)
        ast_node_sims.append(sims["node_jaccard"])
        ast_call_sims.append(sims["call_jaccard"])
    result["max_ast_node_jaccard"] = max(ast_node_sims) if ast_node_sims else 0.0
    result["max_ast_call_jaccard"] = max(ast_call_sims) if ast_call_sims else 0.0

    # Function reuse.
    result["snippet_functions_called"] = count_called_functions_from_snippets(
        code, snippets
    )

    # Nearest distances to gold/distractor/reference.
    gold_snippets = contexts.get("gold", {}).get(task_id, [])
    distractor_snippets = contexts.get("distractor", {}).get(task_id, [])
    result["distance_to_gold"] = nearest_distance(code, gold_snippets)
    result["distance_to_distractor"] = nearest_distance(code, distractor_snippets)

    task = tasks.get(task_id, {})
    ref_solution = load_reference_solution(task)
    if ref_solution:
        result["distance_to_reference"] = 1.0 - char_similarity(code, ref_solution)
    else:
        result["distance_to_reference"] = None

    # Distractor-specific marker inheritance.
    marker_info = inherited_distractor_markers(
        code, gold_snippets, distractor_snippets
    )
    result.update(marker_info)

    # Reuse classification.
    result["reuse_class"] = classify_reuse(
        condition=condition,
        passed=passed,
        max_char_sim=result["max_char_similarity"],
        max_token_jaccard=result["max_token_jaccard"],
        snippet_functions_called=result["snippet_functions_called"],
        n_distractor_markers=result["n_distractor_specific_markers"],
        dist_to_distractor=result["distance_to_distractor"],
        dist_to_gold=result["distance_to_gold"],
        thresholds=thresholds,
    )

    return result


def build_thresholds(args: argparse.Namespace) -> dict[str, float]:
    """Build the threshold dictionary from CLI arguments."""
    return {
        "direct_reuse_char": args.direct_reuse_char,
        "direct_reuse_token": args.direct_reuse_token,
        "adapted_reuse_char": args.adapted_reuse_char,
        "adapted_reuse_token": args.adapted_reuse_token,
        "adapted_min_functions": args.adapted_min_functions,
        "distractor_min_markers": args.distractor_min_markers,
    }


def write_summary_csv(df: pd.DataFrame, output_dir: Path) -> Path:
    """Aggregate reuse class counts/percentages and write the summary CSV."""
    df = df.copy()
    df["level"] = df["task_id"].apply(
        lambda tid: "L1" if "_l1_" in tid else ("L2" if "_l2_" in tid else "L3")
    )

    grouped = (
        df.groupby(["model", "condition", "level", "reuse_class"])
        .size()
        .reset_index(name="count")
    )
    totals = (
        df.groupby(["model", "condition", "level"]).size().reset_index(name="total")
    )
    summary = pd.merge(
        grouped,
        totals,
        on=["model", "condition", "level"],
        how="left",
    )
    summary["percentage"] = summary["count"] / summary["total"] * 100

    # Also add overall correctness by reuse class.
    correctness = (
        df.groupby(["model", "condition", "level", "reuse_class"])
        .agg(passed_count=("passed", "sum"), n=("passed", "count"))
        .reset_index()
    )
    correctness["pass_rate"] = correctness["passed_count"] / correctness["n"] * 100
    summary = pd.merge(
        summary,
        correctness[["model", "condition", "level", "reuse_class", "pass_rate", "n"]],
        on=["model", "condition", "level", "reuse_class"],
        how="left",
    )

    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    path = tables_dir / "reuse_mechanism_summary.csv"
    summary.to_csv(path, index=False, float_format="%.3f")
    print(f"Wrote summary to {path}")
    return path


def write_distractor_inheritance_csv(df: pd.DataFrame, output_dir: Path) -> Path:
    """Write detailed distractor error inheritance records."""
    mask = df["reuse_class"] == "distractor_error_inheritance"
    distractor_df = df[mask].copy()
    if distractor_df.empty:
        # Write header-only file so downstream tools still find the path.
        distractor_df = pd.DataFrame(
            columns=[
                "task_id",
                "model",
                "condition",
                "strategy",
                "sample_id",
                "passed",
                "max_char_similarity",
                "max_token_jaccard",
                "distance_to_gold",
                "distance_to_distractor",
                "snippet_functions_called",
                "n_distractor_specific_markers",
                "distractor_specific_literals",
                "distractor_specific_functions",
            ]
        )
    cols = [
        "task_id",
        "model",
        "condition",
        "strategy",
        "sample_id",
        "passed",
        "max_char_similarity",
        "max_token_jaccard",
        "distance_to_gold",
        "distance_to_distractor",
        "snippet_functions_called",
        "n_distractor_specific_markers",
        "distractor_specific_literals",
        "distractor_specific_functions",
    ]
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    path = tables_dir / "distractor_error_inheritance.csv"
    distractor_df[[c for c in cols if c in distractor_df.columns]].to_csv(
        path, index=False, float_format="%.3f"
    )
    print(f"Wrote distractor inheritance details to {path}")
    return path


def plot_reuse_vs_correctness(df: pd.DataFrame, output_dir: Path) -> Path:
    """Bar plot of reuse class distribution by correctness."""
    sns.set_style("whitegrid")
    counts = (
        df.groupby(["reuse_class", "passed"]).size().reset_index(name="count")
    )
    counts["correct"] = counts["passed"].map({True: "passed", False: "failed"})

    plt.figure(figsize=(10, 6))
    ax = sns.barplot(
        data=counts,
        x="reuse_class",
        y="count",
        hue="correct",
        order=REUSE_CLASSES,
        palette="Set2",
    )
    ax.set_xlabel("Reuse Mechanism")
    ax.set_ylabel("Number of Records")
    ax.set_title("Reuse Mechanism vs. Test Correctness")
    for label in ax.get_xticklabels():
        label.set_rotation(30)
        label.set_horizontalalignment("right")
    plt.legend(title="Outcome")
    plt.tight_layout()
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    path = figures_dir / "reuse_vs_correctness.pdf"
    plt.savefig(path, dpi=300)
    print(f"Wrote figure to {path}")
    plt.close()
    return path


def plot_distractor_inheritance_by_model(df: pd.DataFrame, output_dir: Path) -> Path:
    """Bar plot of distractor error inheritance rate per model."""
    distractor_df = df[
        df["condition"].isin(
            {"distractor", "distractor_reminder_mild", "distractor_reminder_strong"}
        )
    ].copy()

    if distractor_df.empty:
        plt.figure(figsize=(6, 4))
        plt.text(0.5, 0.5, "No distractor records", ha="center", va="center")
        path = output_dir / "distractor_inheritance_by_model.pdf"
        plt.savefig(path, dpi=300)
        plt.close()
        return path

    summary = (
        distractor_df.groupby("model")
        .agg(
            inheritance_count=(
                "reuse_class",
                lambda x: (x == "distractor_error_inheritance").sum(),
            ),
            total=("reuse_class", "count"),
        )
        .reset_index()
    )
    summary["inheritance_rate"] = summary["inheritance_count"] / summary["total"] * 100

    sns.set_style("whitegrid")
    plt.figure(figsize=(10, 6))
    ax = sns.barplot(
        data=summary,
        x="model",
        y="inheritance_rate",
        hue="model",
        legend=False,
        palette="muted",
    )
    ax.set_xlabel("Model")
    ax.set_ylabel("Distractor Error Inheritance Rate (%)")
    ax.set_title("Distractor Error Inheritance by Model")
    for label in ax.get_xticklabels():
        label.set_rotation(30)
        label.set_horizontalalignment("right")
    plt.tight_layout()
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    path = figures_dir / "distractor_inheritance_by_model.pdf"
    plt.savefig(path, dpi=300)
    print(f"Wrote figure to {path}")
    plt.close()
    return path


def run_analysis(
    raw_path: Path,
    test_results_path: Path,
    output_dir: Path,
    thresholds: dict[str, float],
    tasks_path: Path = TASKS_FILE,
) -> pd.DataFrame:
    """Run the full reuse mechanism analysis."""
    raw_records: dict[tuple[str, ...], dict[str, Any]] = {}
    with raw_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            raw_records[record_key(rec)] = rec

    test_records: dict[tuple[str, ...], dict[str, Any]] = {}
    with test_results_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            test_records[record_key(rec)] = rec

    common_keys = set(raw_records.keys()) & set(test_records.keys())
    missing_in_test = set(raw_records.keys()) - set(test_records.keys())
    missing_in_raw = set(test_records.keys()) - set(raw_records.keys())
    if missing_in_test:
        print(f"Warning: {len(missing_in_test)} raw records missing test results")
    if missing_in_raw:
        print(f"Warning: {len(missing_in_raw)} test records missing raw generations")

    contexts = load_all_reference_contexts()
    tasks = load_tasks(tasks_path)

    features: list[dict[str, Any]] = []
    for key in sorted(common_keys):
        raw_rec = raw_records[key]
        test_rec = test_records[key]
        merged = {**raw_rec, **test_rec}
        features.append(compute_record_features(merged, contexts, tasks, thresholds))

    df = pd.DataFrame(features)
    output_dir.mkdir(parents=True, exist_ok=True)

    write_summary_csv(df, output_dir)
    write_distractor_inheritance_csv(df, output_dir)
    plot_reuse_vs_correctness(df, output_dir)
    plot_distractor_inheritance_by_model(df, output_dir)

    return df


def _make_smoke_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Create synthetic raw/test records for the smoke test."""
    raw_records = []
    test_records = []

    base_raw = {
        "model": "smoke-model",
        "model_alias": "smoke-model",
        "backend": "smoke",
        "strategy": "standard",
        "sample_id": 0,
        "seed": None,
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": 1024,
        "thinking": "disabled",
        "prompt_hash": "deadbeef",
        "prompt_tokens": 10,
        "completion_tokens": 10,
        "raw_output": "",
        "reasoning_content": "",
        "reasoning_tokens": None,
        "response_id": "r1",
        "response_model": "smoke-model",
        "finish_reason": "stop",
        "error": None,
        "timestamp": "2026-07-11T00:00:00+00:00",
    }

    # Borrow an existing gold snippet so the direct-reuse case reaches the
    # high-similarity threshold with a real retrieval context.
    with (RETRIEVAL_CONTEXTS_DIR / "gold" / "fluxon.json").open(
        encoding="utf-8"
    ) as f:
        gold_ctx = json.load(f)
    gold_snippet = gold_ctx["fluxon_l1_001"][0]

    # Direct reuse: near-verbatim copy of a gold snippet renamed to solve.
    code_direct = gold_snippet.replace(
        "def compute_fluxon_checksum(", "def solve("
    ).replace("payload: str, version: int", "packet: str")
    raw_direct = {
        **base_raw,
        "task_id": "fluxon_l1_001",
        "condition": "gold",
        "generated_code": code_direct,
    }
    test_direct = {
        **base_raw,
        **raw_direct,
        "passed": True,
        "visible_passed": True,
        "hidden_passed": True,
        "error_type": None,
        "error_message": None,
        "first_failed_test": None,
    }
    raw_records.append(raw_direct)
    test_records.append(test_direct)

    # Independent solution under no retrieval.
    code_indep = "def solve(packet: str) -> int:\n    parts = packet.split('::')\n    return int(parts[-1])\n"
    raw_indep = {
        **base_raw,
        "task_id": "fluxon_l1_001",
        "condition": "no",
        "generated_code": code_indep,
    }
    test_indep = {
        **base_raw,
        **raw_indep,
        "passed": False,
        "visible_passed": False,
        "hidden_passed": False,
        "error_type": "Assertion Error",
        "error_message": "assert failed",
        "first_failed_test": "assert solve('FXN::3::alpha::F4::64') == 64",
    }
    raw_records.append(raw_indep)
    test_records.append(test_indep)

    # Distractor error inheritance: uses distractor-specific functions and fails.
    code_distractor = (
        "def solve(packet: str) -> int:\n"
        "    record = parse_fluxon_packet_wrong_key(packet)\n"
        "    return compute_fluxon_checksum_wrong_mod(record['payload'], record['ver'])\n"
    )
    raw_distractor = {
        **base_raw,
        "task_id": "fluxon_l1_001",
        "condition": "distractor",
        "generated_code": code_distractor,
    }
    test_distractor = {
        **base_raw,
        **raw_distractor,
        "passed": False,
        "visible_passed": False,
        "hidden_passed": False,
        "error_type": "Assertion Error",
        "error_message": "wrong result",
        "first_failed_test": "assert solve('FXN::3::alpha::F4::64') == 64",
    }
    raw_records.append(raw_distractor)
    test_records.append(test_distractor)

    return raw_records, test_records


def run_smoke_test(output_dir: Path | None = None) -> None:
    """Run the analysis on synthetic data and assert expected behavior."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        raw_path = tmp_path / "raw.jsonl"
        test_path = tmp_path / "test.jsonl"
        out_dir = output_dir or (tmp_path / "results")

        raw_records, test_records = _make_smoke_records()
        with raw_path.open("w", encoding="utf-8") as f:
            for rec in raw_records:
                f.write(json.dumps(rec) + "\n")
        with test_path.open("w", encoding="utf-8") as f:
            for rec in test_records:
                f.write(json.dumps(rec) + "\n")

        thresholds = build_thresholds(
            argparse.Namespace(
                direct_reuse_char=DIRECT_REUSE_CHAR_THRESHOLD,
                direct_reuse_token=DIRECT_REUSE_TOKEN_THRESHOLD,
                adapted_reuse_char=ADAPTED_REUSE_CHAR_THRESHOLD,
                adapted_reuse_token=ADAPTED_REUSE_TOKEN_THRESHOLD,
                adapted_min_functions=ADAPTED_REUSE_MIN_FUNCTIONS_CALLED,
                distractor_min_markers=DISTRACTOR_SPECIFIC_MIN_MARKERS,
            )
        )
        df = run_analysis(raw_path, test_path, out_dir, thresholds)

        assert len(df) == 3, f"Expected 3 records, got {len(df)}"
        classes = set(df["reuse_class"])
        expected = {
            "direct_reuse",
            "independent_solution",
            "distractor_error_inheritance",
        }
        assert expected <= classes, f"Missing expected classes: {expected - classes}"
        assert (out_dir / "tables" / "reuse_mechanism_summary.csv").exists()
        assert (out_dir / "tables" / "distractor_error_inheritance.csv").exists()
        assert (out_dir / "figures" / "reuse_vs_correctness.pdf").exists()
        assert (out_dir / "figures" / "distractor_inheritance_by_model.pdf").exists()
        print("Smoke test passed.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze reuse mechanisms in retrieval-augmented code generation."
    )
    parser.add_argument(
        "raw_generation_file",
        type=Path,
        nargs="?",
        default=None,
        help="JSONL file with raw generations (required unless --smoke-test)",
    )
    parser.add_argument(
        "test_results_file",
        type=Path,
        nargs="?",
        default=None,
        help="JSONL file with test results (required unless --smoke-test)",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        nargs="?",
        default=RESULTS_DIR,
        help="Directory for output tables and figures (default: results/)",
    )
    parser.add_argument(
        "--direct-reuse-char",
        type=float,
        default=DIRECT_REUSE_CHAR_THRESHOLD,
        help="Char similarity threshold for direct reuse",
    )
    parser.add_argument(
        "--direct-reuse-token",
        type=float,
        default=DIRECT_REUSE_TOKEN_THRESHOLD,
        help="Token Jaccard threshold for direct reuse",
    )
    parser.add_argument(
        "--adapted-reuse-char",
        type=float,
        default=ADAPTED_REUSE_CHAR_THRESHOLD,
        help="Char similarity threshold for adapted reuse",
    )
    parser.add_argument(
        "--adapted-reuse-token",
        type=float,
        default=ADAPTED_REUSE_TOKEN_THRESHOLD,
        help="Token Jaccard threshold for adapted reuse",
    )
    parser.add_argument(
        "--adapted-min-functions",
        type=int,
        default=ADAPTED_REUSE_MIN_FUNCTIONS_CALLED,
        help="Minimum snippet functions called to count as adapted reuse",
    )
    parser.add_argument(
        "--distractor-min-markers",
        type=int,
        default=DISTRACTOR_SPECIFIC_MIN_MARKERS,
        help="Minimum distractor-specific markers for error inheritance",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run a synthetic smoke test instead of processing files",
    )
    parser.add_argument(
        "--tasks",
        type=Path,
        default=TASKS_FILE,
        help="Task definitions JSONL (default: tasks/all_tasks.jsonl)",
    )
    args = parser.parse_args()

    if args.smoke_test:
        run_smoke_test()
        return

    if not args.raw_generation_file.exists():
        print(f"Error: raw generation file not found: {args.raw_generation_file}")
        sys.exit(1)
    if not args.test_results_file.exists():
        print(f"Error: test results file not found: {args.test_results_file}")
        sys.exit(1)

    thresholds = build_thresholds(args)
    run_analysis(
        args.raw_generation_file,
        args.test_results_file,
        args.output_dir,
        thresholds,
        tasks_path=args.tasks,
    )
    print("Reuse mechanism analysis complete.")


if __name__ == "__main__":
    main()
