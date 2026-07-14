#!/usr/bin/env python3
"""Fast retry of DeepSeek empty records with short timeouts and concurrency."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import openai
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from run_generation import extract_code

load_dotenv(ROOT / ".env")

PLACEHOLDER = "raise NotImplementedError('API retry failed; placeholder')"


def get_client() -> openai.AsyncOpenAI:
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not set")
    return openai.AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=30)


async def generate_one(
    client: openai.AsyncOpenAI, prompt: str, params: dict[str, Any], sem: asyncio.Semaphore
) -> dict[str, Any] | None:
    async with sem:
        messages = [
            {"role": "system", "content": "You are an expert Python programmer."},
            {"role": "user", "content": prompt},
        ]
        for attempt in range(2):
            try:
                coro = client.chat.completions.create(
                    model="deepseek-v4-flash",
                    messages=messages,
                    temperature=params.get("temperature", 0.7),
                    top_p=params.get("top_p", 1.0),
                    max_tokens=params.get("max_tokens", 4096),
                    seed=params.get("seed"),
                )
                response = await asyncio.wait_for(coro, timeout=30)
                choice = response.choices[0]
                content = choice.message.content or ""
                return {
                    "raw_output": content,
                    "generated_code": extract_code(content),
                    "response_model": response.model,
                    "response_id": response.id,
                    "finish_reason": choice.finish_reason,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None,
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                }
            except asyncio.TimeoutError:
                print(f"    attempt {attempt + 1} timed out", flush=True)
            except Exception as e:
                print(f"    attempt {attempt + 1} failed: {e}", flush=True)
            await asyncio.sleep(2 ** attempt)
    return None


async def main_async() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--placeholder", action="store_true", default=True)
    args = parser.parse_args()

    client = get_client()
    sem = asyncio.Semaphore(args.concurrency)

    with args.path.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f]

    empty_indices = [i for i, rec in enumerate(records) if not rec.get("generated_code", "").strip()]
    print(f"Found {len(empty_indices)} empty records", flush=True)
    if not empty_indices:
        return 0

    async def retry_idx(idx: int) -> None:
        rec = records[idx]
        label = f"{rec['task_id']} / {rec['condition']} / sample {rec['sample_id']}"
        print(f"Retrying {idx}: {label}", flush=True)
        params = {
            "temperature": rec.get("temperature", 0.7),
            "top_p": rec.get("top_p", 1.0),
            "max_tokens": args.max_tokens,
            "seed": rec.get("seed"),
        }
        result = await generate_one(client, rec["prompt"], params, sem)
        if result and result["generated_code"]:
            rec.update(result)
            rec["max_tokens"] = args.max_tokens
            print(f"  fixed {label}", flush=True)
        else:
            print(f"  still empty {label}", flush=True)
            if args.placeholder:
                rec["generated_code"] = PLACEHOLDER
                rec["raw_output"] = PLACEHOLDER
                rec["finish_reason"] = "placeholder"
                rec["max_tokens"] = args.max_tokens

    await asyncio.gather(*(retry_idx(i) for i in empty_indices))

    fixed = sum(1 for i in empty_indices if records[i].get("generated_code") and records[i].get("generated_code") != PLACEHOLDER)
    placeholders = sum(1 for i in empty_indices if records[i].get("generated_code") == PLACEHOLDER)
    print(f"Fixed {fixed}/{len(empty_indices)}; placeholders {placeholders}", flush=True)

    with args.path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
