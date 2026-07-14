#!/usr/bin/env bash
# Run P1 codellama after P0 qwen7b CoT finishes so only one local model uses the GPU.
set -uo pipefail

cd "$(dirname "$0")/.."

P0_QWEN7B_RAW="outputs/raw_generations/p0_qwen7b_cot.jsonl"
P0_QWEN7B_RESULTS="outputs/test_results/p0_qwen7b_cot_results.jsonl"

echo "[$(date)] Waiting for P0 qwen7b CoT to finish: ${P0_QWEN7B_RESULTS}"
while [ ! -f "${P0_QWEN7B_RESULTS}" ] || [ "$(wc -l < "${P0_QWEN7B_RAW}" 2>/dev/null || echo 0)" -lt 1350 ]; do
    sleep 60
done

echo "[$(date)] P0 qwen7b done. Starting P1 codellama Pass@3."
python scripts/run_generation.py \
    --model codellama \
    --conditions no naive gold distractor \
    --strategy standard \
    --n-samples 3 \
    --seed 42 \
    --temperature 0.7 \
    --output p1_codellama_n3.jsonl \
    > outputs/p1_codellama.log 2>&1

echo "[$(date)] Evaluating P1 codellama."
python scripts/run_tests.py \
    outputs/raw_generations/p1_codellama_n3.jsonl \
    outputs/test_results/p1_codellama_n3_results.jsonl \
    >> outputs/p1_codellama.log 2>&1

echo "[$(date)] Computing P1 codellama Pass@k."
python scripts/compute_passatk.py \
    outputs/test_results/p1_codellama_n3_results.jsonl \
    --max-k 3 --by-level \
    >> outputs/p1_codellama.log 2>&1

echo "[$(date)] P1 codellama done."
