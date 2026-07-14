#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ../.venv/bin/activate 2>/dev/null || true
export PYTHONUNBUFFERED=1
export CUDA_VISIBLE_DEVICES=0

LOG="realworld/outputs/status/e9_local.log"
mkdir -p realworld/outputs/status

echo "[$(date -Iseconds)] Starting E9 local experiments" | tee "$LOG"

run_local () {
  local model=$1
  local backend=$2
  local out=$3
  if [ -f "realworld/outputs/raw_generations/$out" ]; then
    echo "[$(date -Iseconds)] Resuming $model -> $out" | tee -a "$LOG"
    mode="a"
  else
    echo "[$(date -Iseconds)] Starting $model -> $out" | tee -a "$LOG"
  fi
  python scripts/run_realworld_generation.py \
    --model "$model" --backend "$backend" \
    --tasks realworld/tasks/realworld_tasks_final.jsonl \
    --conditions no naive gold distractor \
    --output "$out" \
    --temperature 0.0 --top-p 1.0 --max-tokens 1024 \
    --strategy standard --num-samples 1 \
    --resume 2>&1 | tee -a "$LOG"
}

run_local qwen3b local e9_qwen3b.jsonl
run_local qwen7b local e9_qwen7b.jsonl
run_local codellama gguf e9_codellama.jsonl

echo "[$(date -Iseconds)] E9 local experiments finished" | tee -a "$LOG"
