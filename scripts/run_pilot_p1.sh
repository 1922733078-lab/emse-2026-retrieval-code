#!/usr/bin/env bash
# Pilot for P1 (Pass@k) experiment: 5 tasks per model, 4 conditions, 3 samples.
set -euo pipefail

cd "$(dirname "$0")/.."
LIMIT=5
N_SAMPLES=3
TEMP=0.7
OUT_DIR="outputs/raw_generations"
TEST_DIR="outputs/test_results"
mkdir -p "$OUT_DIR" "$TEST_DIR"

run_model() {
    local alias=$1
    echo "[Pilot P1] Generating for $alias ..."
    python scripts/run_generation.py \
        --model "$alias" \
        --conditions no naive gold distractor \
        --strategy standard \
        --n-samples "$N_SAMPLES" \
        --seed 42 \
        --temperature "$TEMP" \
        --limit "$LIMIT" \
        --output "pilot_p1_${alias}.jsonl"

    echo "[Pilot P1] Evaluating $alias ..."
    python scripts/run_tests.py \
        "${OUT_DIR}/pilot_p1_${alias}.jsonl" \
        "${TEST_DIR}/pilot_p1_${alias}_results.jsonl"

    echo "[Pilot P1] Pass@k for $alias:"
    python scripts/compute_passatk.py \
        "${TEST_DIR}/pilot_p1_${alias}_results.jsonl" \
        --max-k 3
}

# Local models (run sequentially to avoid OOM on a single GPU).
for alias in qwen3b qwen7b codellama; do
    run_model "$alias"
done

# API model.
run_model deepseek_v4_flash

echo "[Pilot P1] Done."
