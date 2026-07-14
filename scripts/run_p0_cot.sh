#!/usr/bin/env bash
# Full P0 (CoT) experiment runner.
set -uo pipefail

cd "$(dirname "$0")/.."

OUT_DIR="outputs/raw_generations"
TEST_DIR="outputs/test_results"
mkdir -p "$OUT_DIR" "$TEST_DIR"

run_model() {
    local alias=$1
    local output="p0_${alias}_cot.jsonl"
    echo "[P0] Starting CoT generation for $alias -> ${output}"
    python scripts/run_generation.py \
        --model "$alias" \
        --conditions no gold distractor \
        --strategy cot \
        --n-samples 1 \
        --temperature 0.0 \
        --output "$output" \
        > "outputs/p0_${alias}.log" 2>&1
    echo "[P0] Generation done for $alias"

    echo "[P0] Evaluating $alias"
    python scripts/run_tests.py \
        "${OUT_DIR}/${output}" \
        "${TEST_DIR}/p0_${alias}_cot_results.jsonl" \
        >> "outputs/p0_${alias}.log" 2>&1
    echo "[P0] Evaluation done for $alias"

    echo "[P0] Metrics for $alias"
    python scripts/compute_passatk.py \
        "${TEST_DIR}/p0_${alias}_cot_results.jsonl" \
        --max-k 1 \
        --by-level \
        >> "outputs/p0_${alias}.log" 2>&1
}

# API model in background.
run_model deepseek_v4_flash &
API_PID=$!

# Local models sequentially.
for alias in qwen3b qwen7b codellama; do
    run_model "$alias"
done

echo "[P0] Waiting for API model ..."
wait "$API_PID"

echo "[P0] All models done. Aggregating ..."
python scripts/compute_passatk.py \
    "${TEST_DIR}/p0_qwen3b_cot_results.jsonl" \
    "${TEST_DIR}/p0_qwen7b_cot_results.jsonl" \
    "${TEST_DIR}/p0_codellama_cot_results.jsonl" \
    "${TEST_DIR}/p0_deepseek_v4_flash_cot_results.jsonl" \
    --max-k 1 \
    --output "outputs/p0_cot_summary.csv" \
    > outputs/p0_aggregate.log 2>&1 || true

echo "[P0] Done. Logs in outputs/p0_*.log"
