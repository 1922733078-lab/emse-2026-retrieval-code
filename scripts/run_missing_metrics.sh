#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ../.venv/bin/activate 2>/dev/null || true

LOG="outputs/status/missing_metrics.log"
echo "[$(date -Iseconds)] Starting missing metrics computation" | tee "$LOG"

for f in \
  p0_qwen3b_cot \
  p0_qwen7b_cot \
  p0_codellama_cot \
  p0_deepseek_v4_flash_cot \
  p1_qwen3b_n3 \
  p1_qwen7b_n3 \
  p1_codellama_n3 \
  p1_deepseek_v4_flash_n3; do
  raw="outputs/raw_generations/${f}.jsonl"
  test="outputs/test_results/${f}_results.jsonl"
  metric="outputs/metrics/${f}_metrics.jsonl"
  if [ -f "$test" ] && [ ! -f "$metric" ]; then
    echo "[$(date -Iseconds)] Computing metrics for $f" | tee -a "$LOG"
    python scripts/compute_metrics.py "$test" "$metric" 2>&1 | tee -a "$LOG"
  else
    echo "[$(date -Iseconds)] Skipping $f (test missing or metric exists)" | tee -a "$LOG"
  fi
done

echo "[$(date -Iseconds)] Missing metrics computation finished" | tee -a "$LOG"
