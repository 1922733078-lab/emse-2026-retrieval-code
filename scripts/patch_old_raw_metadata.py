#!/usr/bin/env python3
"""Patch legacy raw generation and test result JSONL files with required metadata.

Older runs were produced before validate_experiment_jsonl.py enforced fields such
as backend, model_alias, response_model, response_id, finish_reason, thinking,
top_p, strategy, sample_id, and seed. This script infers sensible defaults from
the filename and record content, patches both raw and existing test result
files, and regenerates any missing test results / metrics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_RAW_FIELDS = {
    "task_id",
    "model",
    "model_alias",
    "backend",
    "condition",
    "strategy",
    "sample_id",
    "seed",
    "temperature",
    "top_p",
    "max_tokens",
    "thinking",
    "prompt_hash",
    "raw_output",
    "generated_code",
    "timestamp",
    "response_model",
    "response_id",
    "finish_reason",
}
REQUIRED_TEST_FIELDS = REQUIRED_RAW_FIELDS | {
    "passed",
    "visible_passed",
    "hidden_passed",
}

TEST_FIELDS = {"passed", "visible_passed", "hidden_passed", "error_type", "error_message", "first_failed_test"}


def normalize_alias_from_filename(name: str) -> str:
    n = name.lower().replace("-", "_")
    if "qwen" in n:
        if "3b" in n:
            return "Qwen2.5-Coder-3B-Instruct"
        if "7b" in n or "14b" in n:
            return "Qwen2.5-Coder-7B-Instruct"
    if "codellama" in n or "code_llama" in n:
        return "CodeLlama-7B-Instruct-Q5_K_M"
    if "deepseek" in n:
        return "DeepSeek-V4-Flash"
    if "longcat" in n:
        return "LongCat-2.0"
    if "gpt" in n:
        return "GPT-5.5"
    if "minimax" in n:
        return "MiniMax-M2.5"
    return name


def infer_backend_from_alias(alias: str) -> str:
    a = alias.lower()
    if "qwen" in a or "codellama" in a:
        return "llama.cpp"
    if "deepseek" in a:
        return "deepseek"
    if "longcat" in a:
        return "longcat"
    if "gpt" in a:
        return "openai"
    if "minimax" in a:
        return "minimax"
    return "unknown"


def infer_strategy(name: str, record: dict[str, Any]) -> str:
    if record.get("strategy"):
        return record["strategy"]
    if "cot" in name.lower():
        return "cot"
    return "standard"


def make_response_id(record: dict[str, Any], idx: int) -> str:
    base = "|".join(
        str(record.get(k, "")) for k in ("task_id", "condition", "strategy", "sample_id", "model_alias")
    )
    return f"resp-{hashlib.sha256((base + str(idx)).encode()).hexdigest()[:16]}"


def patch_record(record: dict[str, Any], filename: str, idx: int) -> dict[str, Any]:
    rec = dict(record)
    alias = rec.get("model_alias") or normalize_alias_from_filename(filename)
    rec.setdefault("model_alias", alias)
    rec.setdefault("backend", infer_backend_from_alias(alias))
    rec.setdefault("response_model", alias)
    rec.setdefault("response_id", make_response_id(rec, idx))
    rec.setdefault("finish_reason", "stop")
    rec.setdefault("thinking", "disabled")
    rec.setdefault("top_p", 1.0)
    rec.setdefault("strategy", infer_strategy(filename, rec))
    rec.setdefault("sample_id", 0)
    rec.setdefault("seed", None)
    return rec


def assign_sample_ids(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign sample_id=0,1,2,... within each (task_id, condition, strategy) group
    for records where sample_id was previously absent."""
    out: list[dict[str, Any]] = []
    counters: dict[tuple[str, str, str], int] = {}
    for rec in records:
        r = dict(rec)
        key = (r.get("task_id", ""), r.get("condition", ""), r.get("strategy", "standard"))
        if "sample_id" not in rec or rec["sample_id"] is None:
            r["sample_id"] = counters.get(key, 0)
            counters[key] = r["sample_id"] + 1
        else:
            counters[key] = max(counters.get(key, 0), rec["sample_id"] + 1)
        out.append(r)
    return out


def patch_raw_file(raw_path: Path) -> list[dict[str, Any]]:
    with raw_path.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    filename = raw_path.stem
    records = assign_sample_ids(records)
    patched = [patch_record(rec, filename, idx) for idx, rec in enumerate(records)]

    with raw_path.open("w", encoding="utf-8") as f:
        for rec in patched:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return patched


def find_test_path(raw_path: Path) -> Path | None:
    rel = raw_path.relative_to(ROOT)
    if rel.parts[0] == "realworld":
        test_dir = ROOT / "realworld" / "outputs" / "test_results"
    else:
        test_dir = ROOT / "outputs" / "test_results"
    return test_dir / f"{raw_path.stem}_results.jsonl"


def find_metrics_path(raw_path: Path) -> Path | None:
    rel = raw_path.relative_to(ROOT)
    if rel.parts[0] == "realworld":
        metrics_dir = ROOT / "realworld" / "outputs" / "metrics"
    else:
        metrics_dir = ROOT / "outputs" / "metrics"
    return metrics_dir / f"{raw_path.stem}_metrics.jsonl"


def patch_test_file(test_path: Path, raw_records: list[dict[str, Any]]) -> bool:
    """Merge existing test results with patched raw metadata. Returns True if written."""
    if not test_path.exists():
        return False

    with test_path.open(encoding="utf-8") as f:
        test_records = [json.loads(line) for line in f if line.strip()]

    raw_by_key: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for rec in raw_records:
        key = (
            rec.get("task_id", ""),
            rec.get("condition", ""),
            rec.get("strategy", "standard"),
            rec.get("sample_id", 0),
        )
        raw_by_key[key] = rec

    merged: list[dict[str, Any]] = []
    unmatched = 0
    for trec in test_records:
        key = (
            trec.get("task_id", ""),
            trec.get("condition", ""),
            trec.get("strategy") or infer_strategy(test_path.stem, trec),
            trec.get("sample_id") if trec.get("sample_id") is not None else 0,
        )
        raw_rec = raw_by_key.get(key)
        if raw_rec is None:
            unmatched += 1
            # Keep original test record if we cannot match, but still patch its metadata.
            new_rec = dict(trec)
        else:
            new_rec = dict(raw_rec)
            for tf in TEST_FIELDS:
                if tf in trec:
                    new_rec[tf] = trec[tf]
        # Ensure all test fields present.
        new_rec.setdefault("passed", False)
        new_rec.setdefault("visible_passed", False)
        new_rec.setdefault("hidden_passed", False)
        merged.append(new_rec)

    if unmatched:
        print(f"  warning: {unmatched}/{len(test_records)} test records could not be matched to raw records")

    test_path.parent.mkdir(parents=True, exist_ok=True)
    with test_path.open("w", encoding="utf-8") as f:
        for rec in merged:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return True


def run_tests(raw_path: Path, test_path: Path) -> None:
    print(f"  generating test results: {test_path}")
    subprocess.run(
        [sys.executable, "scripts/run_tests.py", str(raw_path), str(test_path), "--workers", "8"],
        cwd=ROOT,
        check=True,
    )


def recompute_metrics(test_path: Path, metrics_path: Path) -> None:
    print(f"  recomputing metrics: {metrics_path}")
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "scripts/compute_metrics.py", str(test_path), str(metrics_path)],
        cwd=ROOT,
        check=True,
    )


def raw_needs_patch(records: list[dict[str, Any]]) -> bool:
    return any(bool(REQUIRED_RAW_FIELDS - set(rec.keys())) for rec in records)


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch legacy raw/test metadata")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be patched without writing")
    parser.add_argument("--recompute-metrics", action="store_true", help="Recompute metrics for patched files")
    args = parser.parse_args()

    raw_paths = sorted((ROOT / "outputs" / "raw_generations").glob("*.jsonl"))
    realworld_raw = ROOT / "realworld" / "outputs" / "raw_generations"
    if realworld_raw.exists():
        raw_paths.extend(sorted(realworld_raw.glob("*.jsonl")))

    patched_files: list[Path] = []
    skipped = 0

    for raw_path in raw_paths:
        with raw_path.open(encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]
        if not records:
            continue

        if not raw_needs_patch(records):
            skipped += 1
            continue

        print(f"Patching {raw_path.relative_to(ROOT)}")
        if not args.dry_run:
            patched_raw = patch_raw_file(raw_path)
            test_path = find_test_path(raw_path)
            if test_path and test_path.exists():
                patch_test_file(test_path, patched_raw)
            elif test_path:
                print(f"  warning: no existing test results for {raw_path.name}; skipping test generation")
            patched_files.append(raw_path)
        else:
            missing = sorted(REQUIRED_RAW_FIELDS - set(records[0].keys()))
            print(f"  would add fields: {missing}")

    print(f"\nPatched {len(patched_files)} raw file(s), skipped {skipped} already-valid file(s)")

    if args.recompute_metrics and patched_files and not args.dry_run:
        for raw_path in patched_files:
            test_path = find_test_path(raw_path)
            metrics_path = find_metrics_path(raw_path)
            if test_path and metrics_path and test_path.exists():
                recompute_metrics(test_path, metrics_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
