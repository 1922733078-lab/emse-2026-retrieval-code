"""Async API code generation for real-world E9 tasks."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import openai
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prompts"))

from prompts import render_prompt
from run_generation import DEFAULT_PARAMS, extract_code

load_dotenv(ROOT / ".env")

TASKS_PATH = ROOT / "realworld" / "tasks" / "realworld_tasks_final.jsonl"
CONTEXTS_DIR = ROOT / "realworld" / "retrieval_contexts"
OUTPUT_DIR = ROOT / "realworld" / "outputs" / "raw_generations"
ERRORS_DIR = ROOT / "realworld" / "outputs" / "errors"
ERRORS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PRICE_PER_1M = {
    "longcat": {"prompt": 0.75, "completion": 2.95},
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_api_client(api: str) -> openai.AsyncOpenAI:
    if api == "deepseek":
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        api_key = os.getenv("DEEPSEEK_API_KEY")
    elif api == "longcat":
        base_url = os.getenv("LONGCAT_BASE_URL", "https://api.longcat.chat/openai/v1")
        api_key = os.getenv("LONGCAT_API_KEY")
    else:
        raise ValueError(f"Unknown API: {api}")
    if not api_key:
        raise ValueError(f"API key not set for {api}")
    timeout = int(os.getenv(f"{api.upper()}_TIMEOUT", "180"))
    return openai.AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=timeout)


def is_retryable_error(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status is not None:
        return status == 429 or status >= 500
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "server error" in msg or "503" in msg or "502" in msg or "504" in msg


async def generate_one(
    client: openai.AsyncOpenAI,
    api: str,
    model_name: str,
    prompt: str,
    params: dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> tuple[str, dict[str, Any], str | None]:
    async with semaphore:
        messages = [
            {"role": "system", "content": "You are an expert Python programmer."},
            {"role": "user", "content": prompt},
        ]
        start = time.time()
        last_error: Exception | None = None
        for attempt in range(6):
            try:
                api_kwargs: dict[str, Any] = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": params.get("temperature", 0.0),
                    "top_p": params.get("top_p", 1.0),
                    "max_tokens": params.get("max_tokens", 1024),
                }
                seed = params.get("seed")
                if seed is not None:
                    api_kwargs["seed"] = seed
                if api == "longcat":
                    api_kwargs["extra_body"] = {"thinking": {"type": params.get("thinking", "disabled")}}

                response = await client.chat.completions.create(**api_kwargs)
                choice = response.choices[0]
                content = choice.message.content or ""
                meta = {
                    "latency": time.time() - start,
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None,
                    "response_model": response.model,
                    "response_id": response.id,
                    "finish_reason": choice.finish_reason,
                    "reasoning_content": getattr(choice.message, "reasoning_content", "") or "",
                    "reasoning_tokens": None,
                }
                return content, meta, None
            except Exception as e:
                last_error = e
                if attempt < 5 and is_retryable_error(e):
                    await asyncio.sleep(2 ** attempt)
                    continue
                break
        meta = {
            "latency": time.time() - start,
            "prompt_tokens": None,
            "completion_tokens": None,
            "response_model": None,
            "response_id": None,
            "finish_reason": None,
            "reasoning_content": None,
            "reasoning_tokens": None,
        }
        return "", meta, str(last_error)


def estimate_cost(api: str, prompt_tokens: int | None, completion_tokens: int | None) -> float | None:
    if api not in PRICE_PER_1M:
        return None
    prices = PRICE_PER_1M[api]
    pt = prompt_tokens or 0
    ct = completion_tokens or 0
    return (pt * prices["prompt"] + ct * prices["completion"]) / 1_000_000


def load_context(task_id: str, condition: str) -> str:
    path = CONTEXTS_DIR / condition / f"{task_id}.txt"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_tasks(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-alias", default=None, help="Alias used in output records")
    parser.add_argument("--api", required=True, choices=["deepseek", "longcat"])
    parser.add_argument("--conditions", nargs="+", default=["no", "naive", "gold", "distractor"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--tasks", default=str(TASKS_PATH))
    parser.add_argument("--strategy", default="standard", choices=["standard", "cot"])
    parser.add_argument("--num-samples", type=int, default=1)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--thinking", default="disabled", choices=["enabled", "disabled"])
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    tasks = load_tasks(Path(args.tasks))
    if args.limit > 0:
        tasks = tasks[:args.limit]
    client = get_api_client(args.api)
    model_alias = args.model_alias or args.model

    params = DEFAULT_PARAMS.copy()
    params["temperature"] = args.temperature
    params["top_p"] = args.top_p
    params["max_tokens"] = args.max_tokens
    params["thinking"] = args.thinking
    params["strategy"] = args.strategy

    output_path = OUTPUT_DIR / args.output
    error_path = ERRORS_DIR / args.output.replace(".jsonl", "_errors.jsonl")

    completed: set[tuple[str, str, str, int]] = set()
    if output_path.exists() and args.resume:
        with output_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    completed.add((rec.get("task_id", ""), rec.get("condition", ""), rec.get("strategy", "standard"), rec.get("sample_id", 0)))
                except json.JSONDecodeError:
                    continue
        print(f"Resuming: found {len(completed)} existing generations in {output_path}")

    semaphore = asyncio.Semaphore(args.concurrency)
    write_lock = asyncio.Lock()
    error_lock = asyncio.Lock()
    generated = 0
    failed = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    estimated_cost = 0.0

    async def worker(task: dict[str, Any], condition: str, sample_id: int) -> None:
        nonlocal generated, failed, total_prompt_tokens, total_completion_tokens, estimated_cost

        key = (task["task_id"], condition, args.strategy, sample_id)
        if key in completed:
            return

        context = load_context(task["task_id"], condition)
        snippets = [context] if context else []
        prompt = render_prompt(
            condition=condition,
            task_description=task["prompt"],
            signature=task["signature"],
            snippets=snippets,
            strategy=args.strategy,
        )
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        sample_seed = args.seed + sample_id if args.seed is not None and args.num_samples > 1 else args.seed
        sample_params = params.copy()
        if sample_seed is not None:
            sample_params["seed"] = sample_seed

        raw_output, meta, error_message = await generate_one(
            client, args.api, args.model, prompt, sample_params, semaphore
        )
        generated_code = extract_code(raw_output)

        record = {
            "task_id": task["task_id"],
            "model": args.model,
            "model_alias": model_alias,
            "backend": args.api,
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
            "error": error_message,
            **meta,
        }

        if error_message is not None:
            failed += 1
            error_record = {
                "task_id": task["task_id"],
                "condition": condition,
                "strategy": args.strategy,
                "sample_id": sample_id,
                "error": error_message,
                "timestamp": now_iso(),
            }
            async with error_lock:
                with error_path.open("a", encoding="utf-8") as ef:
                    ef.write(json.dumps(error_record, ensure_ascii=False) + "\n")
            return

        async with write_lock:
            with output_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            generated += 1
            pt = meta.get("prompt_tokens")
            ct = meta.get("completion_tokens")
            if pt is not None:
                total_prompt_tokens += pt
            if ct is not None:
                total_completion_tokens += ct
            cost = estimate_cost(args.api, pt, ct)
            if cost is not None:
                estimated_cost += cost
            if generated % 20 == 0:
                print(
                    f"Progress: {generated} generated, {failed} failed, "
                    f"tokens(p/c)={total_prompt_tokens}/{total_completion_tokens}, "
                    f"est_cost=${estimated_cost:.4f}",
                    flush=True,
                )

    tasks_to_run = [
        worker(task, condition, sample_id)
        for task in tasks
        for condition in args.conditions
        for sample_id in range(args.num_samples)
        if (task["task_id"], condition, args.strategy, sample_id) not in completed
    ]
    skipped = len(tasks) * len(args.conditions) * args.num_samples - len(tasks_to_run)
    if skipped > 0:
        print(f"Skipping {skipped} already-generated combos")
    if not tasks_to_run:
        print("Nothing to generate.")
        return
    await asyncio.gather(*tasks_to_run)
    print(
        f"Wrote {generated} generations to {output_path}; "
        f"logged {failed} failures to {error_path}; "
        f"est_cost=${estimated_cost:.4f}"
    )


if __name__ == "__main__":
    asyncio.run(main_async())
