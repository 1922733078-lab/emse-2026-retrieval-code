#!/usr/bin/env bash
# Start P0 qwen7b CoT as soon as P1 qwen7b Pass@3 generation + evaluation finish.
set -uo pipefail

cd "$(dirname "$0")/.."

TARGET_RESULT="outputs/test_results/p1_qwen7b_n3_results.jsonl"

echo "[$(date)] Waiting for P1 qwen7b results: ${TARGET_RESULT}"
while [ ! -f "${TARGET_RESULT}" ]; do
    sleep 60
done

echo "[$(date)] P1 qwen7b done. Starting P0 qwen7b CoT."
python scripts/run_generation.py \
    --model qwen7b \
    --conditions no gold distractor \
    --strategy cot \
    --n-samples 1 \
    --temperature 0.0 \
    --output p0_qwen7b_cot.jsonl \
    > outputs/p0_qwen7b.log 2>&1

echo "[$(date)] Evaluating P0 qwen7b CoT."
python scripts/run_tests.py \
    outputs/raw_generations/p0_qwen7b_cot.jsonl \
    outputs/test_results/p0_qwen7b_cot_results.jsonl \
    >> outputs/p0_qwen7b.log 2>&1

echo "[$(date)] Computing P0 qwen7b CoT metrics."
python scripts/compute_passatk.py \
    outputs/test_results/p0_qwen7b_cot_results.jsonl \
    --max-k 1 --by-level \
    >> outputs/p0_qwen7b.log 2>&1

echo "[$(date)] P0 qwen7b CoT done."
