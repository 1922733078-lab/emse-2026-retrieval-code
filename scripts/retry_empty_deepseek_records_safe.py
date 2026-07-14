#!/usr/bin/env python3
"""Safely retry DeepSeek empty records with larger max_tokens.

Uses async requests with a tight per-request timeout to avoid the hangs seen
with the synchronous batch retry script.
"""

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

PLACEHOLDER_CODE = "raise NotImplementedError('API retry failed; placeholder')"


def get_client() -> openai.AsyncOpenAI:
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not set")
    return openai.AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=60)


async def generate_one(
    client: openai.AsyncOpenAI,
    prompt: str,
    params: dict[str, Any],
    request_timeout: float = 90.0,
) -> dict[str, Any] | None:
    messages = [
        {"role": "system", "content": "You are an expert Python programmer."},
        {"role": "user", "content": prompt},
    ]
    for attempt in range(3):
        try:
            coro = client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=messages,
                temperature=params.get("temperature", 0.7),
                top_p=params.get("top_p", 1.0),
                max_tokens=params.get("max_tokens", 4096),
                seed=params.get("seed"),
            )
            response = await asyncio.wait_for(coro, timeout=request_timeout)
            choice = response.choices[0]
            content = choice.message.content or ""
            if content:
                return {
                    "raw_output": content,
                    "generated_code": extract_code(content),
                    "response_model": response.model,
                    "response_id": response.id,
                    "finish_reason": choice.finish_reason,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None,
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                }
            # Content empty but call succeeded; return it so caller can decide.
            return {
                "raw_output": "",
                "generated_code": "",
                "response_model": response.model,
                "response_id": response.id,
                "finish_reason": choice.finish_reason,
                "completion_tokens": response.usage.completion_tokens if response.usage else None,
                "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
            }
        except asyncio.TimeoutError:
            print(f"  attempt {attempt + 1} timed out")
        except Exception as e:
            print(f"  attempt {attempt + 1} failed: {e}")
        await asyncio.sleep(2 ** attempt)
    return None


async def main_async() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, help="Raw generations JSONL")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--placeholder-on-failure", action="store_true", default=True)
    args = parser.parse_args()

    client = get_client()
    semaphore = asyncio.Semaphore(args.concurrency)

    records: list[dict[str, Any]] = []
    with args.path.open(encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    empty_indices = [i for i, rec in enumerate(records) if not rec.get("generated_code")]
    print(f"Found {len(empty_indices)} empty records in {args.path}")
    if not empty_indices:
        return 0

    async def retry_idx(idx: int) -> None:
        async with semaphore:
            rec = records[idx]
            label = f"{rec['task_id']} / {rec['condition']} / sample {rec['sample_id']}"
            print(f"Retrying {idx + 1}: {label}")
            params = {
                "temperature": rec.get("temperature", 0.7),
                "top_p": rec.get("top_p", 1.0),
                "max_tokens": args.max_tokens,
                "seed": rec.get("seed"),
            }
            result = await generate_one(client, rec["prompt"], params, request_timeout=args.timeout)
            if result and result["generated_code"]:
                rec.update(result)
                rec["max_tokens"] = args.max_tokens
                print(f"  fixed {label}")
            else:
                print(f"  still empty after retries: {label}")
                if args.placeholder_on_failure:
                    rec["generated_code"] = PLACEHOLDER_CODE
                    rec["raw_output"] = PLACEHOLDER_CODE
                    rec["finish_reason"] = "placeholder"
                    rec["max_tokens"] = args.max_tokens
                    print(f"  filled placeholder for {label}")

    await asyncio.gather(*(retry_idx(i) for i in empty_indices))

    fixed = sum(1 for i in empty_indices if records[i].get("generated_code") and records[i].get("generated_code") != PLACEHOLDER_CODE)
    placeholders = sum(1 for i in empty_indices if records[i].get("generated_code") == PLACEHOLDER_CODE)
    print(f"Fixed {fixed}/{len(empty_indices)} records; placeholders {placeholders}")

    with args.path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
