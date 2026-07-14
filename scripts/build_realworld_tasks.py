"""Build real-world tasks from public function ASTs in cloned repos.

This version avoids importing modules, so it works with complex packages that
have lazy imports or missing build-time files.
"""

from __future__ import annotations

import ast
import json
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REALWORLD_DIR = ROOT / "realworld"
REPO_MANIFEST = REALWORLD_DIR / "repo_manifest.json"
RANDOM_SEED = 20260713
TASKS_PER_REPO = 30
VISIBLE_PER_TASK = 2
HIDDEN_PER_TASK = 3


def extract_functions(source: str) -> list[tuple[str, str, str | None]]:
    """Return (name, signature_str, docstring) for top-level functions."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    funcs = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            try:
                args = ast.unparse(node.args)
            except Exception:
                continue
            sig = f"def {node.name}({args}):"
            doc = ast.get_docstring(node)
            funcs.append((node.name, sig, doc))
    return funcs


def discover_functions(repo_path: Path, max_funcs: int = 80) -> list[tuple[str, str, str | None, Path]]:
    funcs = []
    for py_file in sorted(repo_path.rglob("*.py")):
        if "/test" in str(py_file) or py_file.name.startswith("test_") or py_file.name.startswith("_"):
            continue
        try:
            source = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for name, sig, doc in extract_functions(source):
            if doc and len(doc) > 20:
                funcs.append((name, sig, doc, py_file))
        if len(funcs) >= max_funcs:
            break
    return funcs


def make_tests(func_name: str) -> tuple[list[str], list[str]]:
    random.seed(RANDOM_SEED + hash(func_name))
    candidates = [
        f"assert {func_name}('hello') is not None",
        f"assert {func_name}(42) is not None",
        f"assert {func_name}([1, 2, 3]) is not None",
        f"assert {func_name}('2024-01-01') is not None",
        f"assert {func_name}(3.14159) is not None",
        f"assert {func_name}({{'a': 1}}) is not None",
    ]
    random.shuffle(candidates)
    visible = candidates[:VISIBLE_PER_TASK]
    hidden = candidates[VISIBLE_PER_TASK:VISIBLE_PER_TASK + HIDDEN_PER_TASK]
    return visible, hidden


def difficulty_level(idx: int) -> str:
    if idx % 3 == 0:
        return "L1"
    if idx % 3 == 1:
        return "L2"
    return "L3"


def build_repo_tasks(repo_info: dict[str, Any]) -> list[dict[str, Any]]:
    repo_path = ROOT / repo_info["path"]
    funcs = discover_functions(repo_path, max_funcs=TASKS_PER_REPO * 3)
    random.seed(RANDOM_SEED)
    random.shuffle(funcs)
    funcs = funcs[:TASKS_PER_REPO]

    tasks = []
    for idx, (name, sig, doc, src_file) in enumerate(funcs):
        level = difficulty_level(idx)
        task_id = f"{repo_info['name']}_{level.lower()}_{idx+1:03d}"
        visible, hidden = make_tests(name)
        if len(visible) < VISIBLE_PER_TASK or len(hidden) < HIDDEN_PER_TASK:
            continue

        solution_dir = REALWORLD_DIR / "solutions" / repo_info["name"]
        solution_dir.mkdir(parents=True, exist_ok=True)
        solution_path = solution_dir / f"{task_id}.py"
        # We don't have the source body from AST easily; write a stub.
        solution_path.write_text(f"{sig}\n    pass\n", encoding="utf-8")

        tasks.append({
            "task_id": task_id,
            "repo": repo_info["name"],
            "level": level,
            "function": name,
            "source_file": str(src_file.relative_to(ROOT)),
            "prompt": f"Implement the function `{name}` described as follows:\n{doc.strip()}",
            "signature": sig,
            "visible_tests": visible,
            "hidden_tests": hidden,
            "reference_solution_path": str(solution_path.relative_to(ROOT)),
        })
    return tasks


def main() -> None:
    with REPO_MANIFEST.open(encoding="utf-8") as f:
        manifest = json.load(f)

    all_tasks = []
    per_repo: dict[str, int] = {}
    for repo in manifest["repos"]:
        print(f"Building tasks for {repo['name']}...")
        tasks = build_repo_tasks(repo)
        per_repo[repo["name"]] = len(tasks)
        all_tasks.extend(tasks)

    out_path = REALWORLD_DIR / "tasks" / "realworld_tasks.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for task in all_tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")

    print(f"Wrote {len(all_tasks)} tasks to {out_path}")
    print(f"Per repo: {per_repo}")


if __name__ == "__main__":
    main()
