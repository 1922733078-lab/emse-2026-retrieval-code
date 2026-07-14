"""Build real-world tasks using installed packages and real function execution."""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REALWORLD_DIR = ROOT / "realworld"
RANDOM_SEED = 20260713
TASKS_PER_REPO = 30
VISIBLE_PER_TASK = 2
HIDDEN_PER_TASK = 3

REPO_MODULES = {
    "python-dateutil": "dateutil",
    "humanize": "humanize",
    "tabulate": "tabulate",
}


def get_module_path(module_name: str) -> Path | None:
    try:
        mod = importlib.import_module(module_name)
        return Path(inspect.getfile(mod))
    except Exception:
        return None


def discover_functions(module_name: str, max_funcs: int = 60) -> list[tuple[str, Any]]:
    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        print(f"Cannot import {module_name}: {e}")
        return []

    funcs = []
    for name, obj in inspect.getmembers(mod, inspect.isfunction):
        if name.startswith("_"):
            continue
        try:
            sig = inspect.signature(obj)
        except Exception:
            continue
        params = list(sig.parameters.values())
        if len(params) < 1 or len(params) > 3:
            continue
        if not obj.__doc__:
            continue
        funcs.append((name, obj))
    return funcs[:max_funcs]


def generate_test_cases(func: Any, func_name: str, n: int) -> list[str] | None:
    """Try to generate n test assertions by executing func on sample inputs."""
    random.seed(RANDOM_SEED + hash(func_name))
    candidates = [
        ("hello",),
        (42,),
        ([1, 2, 3],),
        ("2024-01-01",),
        (3.14159,),
        ({"a": 1},),
        ("world", "fmt"),
        (100,),
        (True,),
        (None,),
    ]
    random.shuffle(candidates)
    tests = []
    for args in candidates:
        if len(tests) >= n:
            break
        try:
            result = func(*args)
            if isinstance(result, (int, float, str, bool)) or result is None:
                arg_reprs = ", ".join(repr(a) for a in args)
                tests.append(f"assert {func_name}({arg_reprs}) == {repr(result)}")
        except Exception:
            continue
    return tests if len(tests) >= n else None


def difficulty_level(idx: int) -> str:
    if idx % 3 == 0:
        return "L1"
    if idx % 3 == 1:
        return "L2"
    return "L3"


def build_repo_tasks(repo_name: str, module_name: str) -> list[dict[str, Any]]:
    funcs = discover_functions(module_name)
    if not funcs:
        return []
    random.seed(RANDOM_SEED)
    random.shuffle(funcs)
    funcs = funcs[:TASKS_PER_REPO]

    tasks = []
    for idx, (name, func) in enumerate(funcs):
        level = difficulty_level(idx)
        task_id = f"{repo_name}_{level.lower()}_{idx+1:03d}"
        sig = inspect.signature(func)
        signature = f"def {name}{sig}:"
        visible = generate_test_cases(func, name, VISIBLE_PER_TASK)
        hidden = generate_test_cases(func, name, VISIBLE_PER_TASK + HIDDEN_PER_TASK)
        if not visible or not hidden or len(hidden) < VISIBLE_PER_TASK + HIDDEN_PER_TASK:
            continue
        hidden = hidden[VISIBLE_PER_TASK:]

        solution_dir = REALWORLD_DIR / "solutions" / repo_name
        solution_dir.mkdir(parents=True, exist_ok=True)
        solution_path = solution_dir / f"{task_id}.py"
        try:
            source = inspect.getsource(func)
        except Exception:
            source = f"{signature}\n    pass\n"
        solution_path.write_text(source, encoding="utf-8")

        tasks.append({
            "task_id": task_id,
            "repo": repo_name,
            "level": level,
            "function": name,
            "prompt": f"Implement the function `{name}` described as follows:\n{func.__doc__.strip()}",
            "signature": signature,
            "visible_tests": visible,
            "hidden_tests": hidden,
            "reference_solution_path": str(solution_path.relative_to(ROOT)),
        })
    return tasks


def main() -> None:
    all_tasks = []
    per_repo = {}
    for repo_name, module_name in REPO_MODULES.items():
        print(f"Building tasks for {repo_name} ({module_name})...")
        tasks = build_repo_tasks(repo_name, module_name)
        per_repo[repo_name] = len(tasks)
        all_tasks.extend(tasks)

    out_path = REALWORLD_DIR / "tasks" / "realworld_tasks_v2.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for task in all_tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")

    print(f"Wrote {len(all_tasks)} tasks to {out_path}")
    print(f"Per repo: {per_repo}")


if __name__ == "__main__":
    main()
