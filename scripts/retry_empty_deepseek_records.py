#!/usr/bin/env python3
"""Retry DeepSeek records that returned empty content, using a larger max_tokens.

The DeepSeek API occasionally returns empty content with finish_reason=length when
max_tokens=1024 is requested for longer prompts. This script finds such records in
a raw JSONL file and re-generates them with max_tokens=4096, updating the file in
place.
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

from run_generation import APIModel, extract_code

load_dotenv(ROOT / ".env")


def get_client() -> openai.OpenAI:
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not set")
    return openai.OpenAI(base_url=base_url, api_key=api_key, timeout=180)


def generate_one(client: openai.OpenAI, prompt: str, params: dict[str, Any]) -> dict[str, Any] | None:
    messages = [
        {"role": "system", "content": "You are an expert Python programmer."},
        {"role": "user", "content": prompt},
    ]
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=messages,
                temperature=params.get("temperature", 0.7),
                top_p=params.get("top_p", 1.0),
                max_tokens=params.get("max_tokens", 4096),
                seed=params.get("seed"),
            )
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
        except Exception as e:
            print(f"  attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, help="Raw generations JSONL")
    parser.add_argument("--max-tokens", type=int, default=4096)
    args = parser.parse_args()

    client = get_client()
    records: list[dict[str, Any]] = []
    with args.path.open(encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    empty_indices = [i for i, rec in enumerate(records) if not rec.get("generated_code")]
    print(f"Found {len(empty_indices)} empty records in {args.path}")
    if not empty_indices:
        return 0

    fixed = 0
    for idx in empty_indices:
        rec = records[idx]
        print(f"Retrying {idx + 1}: {rec['task_id']} / {rec['condition']} / sample {rec['sample_id']}")
        params = {
            "temperature": rec.get("temperature", 0.7),
            "top_p": rec.get("top_p", 1.0),
            "max_tokens": args.max_tokens,
            "seed": rec.get("seed"),
        }
        result = generate_one(client, rec["prompt"], params)
        if result and result["generated_code"]:
            rec.update(result)
            rec["max_tokens"] = args.max_tokens
            fixed += 1
        else:
            print(f"  still empty after retries")

    print(f"Fixed {fixed}/{len(empty_indices)} records")
    with args.path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
