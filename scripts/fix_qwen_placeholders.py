#!/usr/bin/env python3
"""Regenerate placeholder records in a local-model JSONL.

A placeholder is generated code containing 'raise NotImplementedError'.  The
script loads the specified local model once, regenerates each placeholder
record using the original prompt/parameters, and updates the file in place.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from run_generation import (
    DEFAULT_PARAMS,
    context_key_for_condition,
    extract_code,
    get_model,
    load_contexts,
    load_tasks,
    now_iso,
    resolve_model,
)
from prompts import render_prompt

PLACEHOLDER_MARKER = "raise NotImplementedError"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen7b")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--tasks", default=str(ROOT / "tasks" / "all_tasks.jsonl"))
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    display_name, model_path_or_name, backend = resolve_model(args.model)
    tasks = {t["task_id"]: t for t in load_tasks(Path(args.tasks))}
    contexts = load_contexts()
    model = get_model(model_path_or_name, backend)

    params = DEFAULT_PARAMS.copy()
    params["temperature"] = args.temperature
    params["top_p"] = args.top_p
    params["max_tokens"] = args.max_tokens
    params["thinking"] = "disabled"
    params["strategy"] = "standard"

    with args.input.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f]

    placeholder_indices = [
        i for i, rec in enumerate(records) if PLACEHOLDER_MARKER in rec.get("generated_code", "")
    ]
    print(f"Found {len(placeholder_indices)} placeholder records in {args.input}")
    if not placeholder_indices:
        return 0

    fixed = 0
    for idx in placeholder_indices:
        rec = records[idx]
        label = f"{rec['task_id']} / {rec['condition']} / sample {rec.get('sample_id', 0)}"
        print(f"Regenerating {idx + 1}: {label}")
        task = tasks.get(rec["task_id"])
        if task is None:
            print(f"  skipping: task definition not found")
            continue
        condition = rec["condition"]
        if condition == "no":
            snippets: list[str] = []
        else:
            ctx_key = context_key_for_condition(condition)
            snippets = contexts.get(ctx_key, {}).get(rec["task_id"], [])

        prompt = render_prompt(
            condition=condition,
            task_description=task["prompt"],
            signature=task["signature"],
            snippets=snippets,
            strategy="standard",
        )

        sample_id = rec.get("sample_id", 0)
        sample_seed = args.seed + sample_id if sample_id > 0 else args.seed
        sample_params = params.copy()
        sample_params["seed"] = sample_seed

        try:
            raw_output, meta = model.generate(prompt, sample_params)
            generated_code = extract_code(raw_output)
        except Exception as e:
            print(f"  generation failed: {e}")
            continue

        rec.update({
            "prompt": prompt,
            "raw_output": raw_output,
            "generated_code": generated_code,
            "timestamp": now_iso(),
            "error": None,
            **meta,
        })
        if generated_code and PLACEHOLDER_MARKER not in generated_code:
            fixed += 1
            print(f"  fixed {label}")
        else:
            print(f"  still placeholder {label}")

    print(f"Fixed {fixed}/{len(placeholder_indices)} placeholders")
    with args.input.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
