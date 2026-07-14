"""Build retrieval contexts for real-world E9 tasks.

For each task we create four contexts:
- no: empty/no snippets
- naive: top-3 functions from the repo whose source or docstring matches task keywords
- gold: source of the function(s) explicitly referenced in the task
- distractor: a function from the same repo with a similar name but different semantics
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REALWORLD = ROOT / "realworld"
TASKS_PATH = REALWORLD / "tasks" / "realworld_tasks_final.jsonl"
OUT_DIR = REALWORLD / "retrieval_contexts"
TOP_K = 3


def extract_functions(repo_path: Path, required_names: set[str] | None = None) -> list[dict[str, Any]]:
    """Walk repo .py files and extract top-level function names with source.

    Required function names are always included even if they start with an
    underscore or live in __init__.py, because some repos expose a tiny public
    API through __init__.py.
    """
    required_names = required_names or set()
    funcs = []
    seen = set()
    for py_file in repo_path.rglob("*.py"):
        # Skip tests, but keep __init__.py when looking for required names
        if "test" in py_file.name.lower():
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                is_public = not node.name.startswith("_")
                is_required = node.name in required_names
                if not (is_public or is_required):
                    continue
                if node.name in seen:
                    continue
                seen.add(node.name)
                funcs.append({
                    "file": str(py_file.relative_to(REALWORLD)),
                    "name": node.name,
                    "source": ast.get_source_segment(source, node) or "",
                    "docstring": ast.get_docstring(node) or "",
                })
    return funcs


def bm25_lite_score(query: str, doc: str) -> float:
    """Very simple keyword overlap score for ranking."""
    qterms = set(re.findall(r"[a-zA-Z_]{3,}", query.lower()))
    dterms = set(re.findall(r"[a-zA-Z_]{3,}", doc.lower()))
    if not qterms:
        return 0.0
    return len(qterms & dterms) / len(qterms)


def find_gold_function(funcs: list[dict], task: dict) -> dict | None:
    """Heuristic: match function names mentioned in prompt/signature."""
    text = task["prompt"] + " " + task.get("signature", "")
    mentioned = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text))
    candidates = [f for f in funcs if f["name"] in mentioned]
    # Prefer the one whose name is most central in the prompt
    candidates.sort(key=lambda f: text.count(f["name"]), reverse=True)
    return candidates[0] if candidates else None


def find_distractor(funcs: list[dict], gold: dict | None, task: dict) -> dict | None:
    """Pick a function with a similar-looking name but not the gold one."""
    if gold is None:
        # Fallback: a function whose name shares a prefix with a mentioned token
        text = task["prompt"] + " " + task.get("signature", "")
        mentioned = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text))
        for m in mentioned:
            for f in funcs:
                if f["name"] != m and (f["name"].startswith(m[:4]) or m.startswith(f["name"][:4])):
                    return f
        return funcs[0] if funcs else None
    # Find a function whose name is an edit/addition to gold name
    best = None
    best_score = -1
    for f in funcs:
        if f["name"] == gold["name"]:
            continue
        # Simple similarity: common substring length
        common = 0
        for i in range(min(len(f["name"]), len(gold["name"]))):
            if f["name"][i] == gold["name"][i]:
                common += 1
        if common > best_score:
            best_score = common
            best = f
    return best


def build_contexts_for_task(task: dict, funcs: list[dict]) -> dict[str, str]:
    gold_func = find_gold_function(funcs, task)
    distractor_func = find_distractor(funcs, gold_func, task)

    # Naive: rank by keyword overlap with prompt
    scored = [(f, bm25_lite_score(task["prompt"], f["source"] + " " + f["docstring"])) for f in funcs]
    scored.sort(key=lambda x: x[1], reverse=True)
    naive_funcs = [f for f, _ in scored[:TOP_K]]

    contexts = {
        "no": "",
        "naive": "\n\n".join(f"```python\n{f['source']}\n```" for f in naive_funcs),
        "gold": f"```python\n{gold_func['source']}\n```" if gold_func else "",
        "distractor": f"```python\n{distractor_func['source']}\n```" if distractor_func else "",
    }
    return contexts


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tasks = [json.loads(l) for l in TASKS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]

    # Gather required function names per repo from task prompts/signatures
    required_by_repo: dict[str, set[str]] = {}
    for task in tasks:
        repo = task["repo"]
        text = task["prompt"] + " " + task.get("signature", "")
        names = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text))
        required_by_repo.setdefault(repo, set()).update(names)

    # Group tasks by repo and load functions once
    repo_funcs: dict[str, list[dict]] = {}
    for task in tasks:
        repo = task["repo"]
        if repo not in repo_funcs:
            repo_path = REALWORLD / "repos" / repo
            if repo == "python-dateutil":
                repo_path = repo_path / "src" / "dateutil"
            elif repo == "humanize":
                repo_path = repo_path / "src" / "humanize"
            elif repo == "tabulate":
                repo_path = repo_path / "tabulate"
            print(f"Loading functions from {repo_path}")
            repo_funcs[repo] = extract_functions(repo_path, required_by_repo.get(repo, set()))
            print(f"  -> {len(repo_funcs[repo])} functions")

    for task in tasks:
        task_id = task["task_id"]
        contexts = build_contexts_for_task(task, repo_funcs[task["repo"]])
        for cond, content in contexts.items():
            cond_dir = OUT_DIR / cond
            cond_dir.mkdir(parents=True, exist_ok=True)
            (cond_dir / f"{task_id}.txt").write_text(content, encoding="utf-8")

    manifest = {
        "task_count": len(tasks),
        "conditions": ["no", "naive", "gold", "distractor"],
        "top_k": TOP_K,
        "note": "Gold/distractor contexts are heuristic and require manual review for final study.",
    }
    (OUT_DIR / "context_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote retrieval contexts for {len(tasks)} tasks to {OUT_DIR}")


if __name__ == "__main__":
    main()
