#!/usr/bin/env bash
# Full P1 (Pass@k) experiment runner.
# Defaults to sequential local models + concurrent API to avoid OOM.
set -uo pipefail

cd "$(dirname "$0")/.."

N_SAMPLES=3
TEMP=0.7
SEED=42
OUT_DIR="outputs/raw_generations"
TEST_DIR="outputs/test_results"
mkdir -p "$OUT_DIR" "$TEST_DIR"

# Optional flags.
CONCURRENT_LOCAL=0
if [ "${1:-}" = "--concurrent-local" ]; then
    CONCURRENT_LOCAL=1
    shift
fi

run_model() {
    local alias=$1
    local output="p1_${alias}_n${N_SAMPLES}.jsonl"
    echo "[P1] Starting generation for $alias -> ${output}"
    python scripts/run_generation.py \
        --model "$alias" \
        --conditions no naive gold distractor \
        --strategy standard \
        --n-samples "$N_SAMPLES" \
        --seed "$SEED" \
        --temperature "$TEMP" \
        --output "$output" \
        > "outputs/p1_${alias}.log" 2>&1
    echo "[P1] Generation done for $alias"

    echo "[P1] Evaluating $alias"
    python scripts/run_tests.py \
        "${OUT_DIR}/${output}" \
        "${TEST_DIR}/p1_${alias}_n${N_SAMPLES}_results.jsonl" \
        >> "outputs/p1_${alias}.log" 2>&1
    echo "[P1] Evaluation done for $alias"

    echo "[P1] Pass@k for $alias"
    python scripts/compute_passatk.py \
        "${TEST_DIR}/p1_${alias}_n${N_SAMPLES}_results.jsonl" \
        --max-k 3 \
        --by-level \
        >> "outputs/p1_${alias}.log" 2>&1
}

# Launch API model in background.
run_model deepseek_v4_flash &
API_PID=$!

# Run local models.
if [ "$CONCURRENT_LOCAL" -eq 1 ]; then
    echo "[P1] Running local models concurrently (monitor VRAM!)"
    for alias in qwen3b qwen7b codellama; do
        run_model "$alias" &
    done
    wait
else
    echo "[P1] Running local models sequentially"
    for alias in qwen3b qwen7b codellama; do
        run_model "$alias"
    done
fi

# Wait for API model.
echo "[P1] Waiting for API model ..."
wait "$API_PID"

echo "[P1] All models done. Aggregating ..."
python scripts/compute_passatk.py \
    "${TEST_DIR}/p1_qwen3b_n${N_SAMPLES}_results.jsonl" \
    "${TEST_DIR}/p1_qwen7b_n${N_SAMPLES}_results.jsonl" \
    "${TEST_DIR}/p1_codellama_n${N_SAMPLES}_results.jsonl" \
    "${TEST_DIR}/p1_deepseek_v4_flash_n${N_SAMPLES}_results.jsonl" \
    --max-k 3 \
    --output "outputs/p1_passatk_summary.csv" \
    > outputs/p1_aggregate.log 2>&1 || true

echo "[P1] Done. Logs in outputs/p1_*.log"
