"""Generate code for real-world E9 tasks across models and retrieval conditions."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prompts"))
sys.path.insert(0, str(ROOT / "scripts"))

from prompts import render_prompt
from run_generation import (
    DEFAULT_PARAMS,
    MODEL_ALIASES,
    extract_code,
    get_model,
    now_iso,
    resolve_model,
)

TASKS_PATH = ROOT / "realworld" / "tasks" / "realworld_tasks_final.jsonl"
CONTEXTS_DIR = ROOT / "realworld" / "retrieval_contexts"
OUTPUT_DIR = ROOT / "realworld" / "outputs" / "raw_generations"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_tasks(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load_context(task_id: str, condition: str) -> str:
    path = CONTEXTS_DIR / condition / f"{task_id}.txt"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def build_output_filename(model_alias: str, strategy: str, num_samples: int) -> str:
    parts = [model_alias, "realworld", strategy]
    if num_samples > 1:
        parts.append(f"n{num_samples}")
    return "_".join(parts) + ".jsonl"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--backend", choices=["openai", "deepseek", "kimi", "gpt", "longcat", "minimax", "local", "gguf"])
    parser.add_argument("--conditions", nargs="+", default=["no", "naive", "gold", "distractor"])
    parser.add_argument("--output")
    parser.add_argument("--tasks", default=str(TASKS_PATH))
    parser.add_argument("--strategy", default="standard", choices=["standard", "cot"])
    parser.add_argument("--num-samples", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--thinking", default="disabled", choices=["enabled", "disabled"])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    try:
        display_name, model_path_or_name, backend = resolve_model(args.model)
    except ValueError:
        if not args.backend:
            raise
        display_name = args.model
        model_path_or_name = args.model
        backend = args.backend

    tasks = load_tasks(Path(args.tasks))
    if args.limit > 0:
        tasks = tasks[:args.limit]
    model = get_model(model_path_or_name, backend)

    params = DEFAULT_PARAMS.copy()
    params["temperature"] = args.temperature
    params["top_p"] = args.top_p
    params["max_tokens"] = args.max_tokens
    params["thinking"] = args.thinking
    params["strategy"] = args.strategy

    output_name = args.output or build_output_filename(args.model, args.strategy, args.num_samples)
    output_path = OUTPUT_DIR / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    completed: set[tuple[str, str, str, int]] = set()
    if args.resume and output_path.exists():
        with output_path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                completed.add((r["task_id"], r["condition"], r.get("strategy", args.strategy), r.get("sample_id", 0)))
        print(f"Resuming: found {len(completed)} existing generations in {output_path}")

    records: list[dict[str, Any]] = []
    for task in tasks:
        task_id = task["task_id"]
        for condition in args.conditions:
            context = load_context(task_id, condition)
            for sample_id in range(args.num_samples):
                key = (task_id, condition, args.strategy, sample_id)
                if key in completed:
                    continue
                snippets = [context] if context else []
                prompt = render_prompt(
                    condition=condition,
                    task_description=task["prompt"],
                    signature=task["signature"],
                    snippets=snippets,
                    strategy=args.strategy,
                )
                prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
                sample_seed = args.seed + sample_id if args.seed is not None else None
                sample_params = params.copy()
                sample_params["seed"] = sample_seed

                raw_output, meta = model.generate(prompt, sample_params)
                generated_code = extract_code(raw_output)

                record = {
                    "task_id": task_id,
                    "model": display_name,
                    "model_alias": args.model,
                    "backend": backend,
                    "condition": condition,
                    "strategy": args.strategy,
                    "sample_id": sample_id,
                    "seed": sample_seed,
                    "temperature": args.temperature,
                    "top_p": args.top_p,
                    "max_tokens": args.max_tokens,
                    "thinking": args.thinking,
                    "prompt_hash": prompt_hash,
                    "prompt": prompt,
                    "raw_output": raw_output,
                    "generated_code": generated_code,
                    "timestamp": now_iso(),
                    "error": None,
                    **meta,
                }
                records.append(record)

    with output_path.open("a" if args.resume else "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} generations to {output_path}")


if __name__ == "__main__":
    main()
