#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ../.venv/bin/activate 2>/dev/null || true
export PYTHONUNBUFFERED=1
export CUDA_VISIBLE_DEVICES=0

LOG="outputs/status/e7_e8_local.log"
echo "[$(date -Iseconds)] Starting E7/E8 local experiments" | tee "$LOG"

run_local () {
  local model=$1
  local conds=$2
  local out=$3
  mode="w"
  [ -f "outputs/raw_generations/$out" ] && mode="a"
  python scripts/run_generation.py \
    --model "$model" \
    --tasks tasks/longcat_pilot_90.jsonl \
    --conditions $conds \
    --output "$out" \
    --temperature 0.0 --top-p 1.0 --max-tokens 1024 \
    --strategy standard --num-samples 1 \
    --resume 2>&1 | tee -a "$LOG"
}

# E7
for model in qwen3b qwen7b codellama; do
  run_local "$model" "dense hybrid" "e7_${model}.jsonl"
done

# E8
for model in qwen3b qwen7b codellama; do
  run_local "$model" "distractor_weak distractor_strong" "e8_${model}.jsonl"
done

echo "[$(date -Iseconds)] E7/E8 local experiments finished" | tee -a "$LOG"
