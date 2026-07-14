#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ../.venv/bin/activate 2>/dev/null || true
export PYTHONUNBUFFERED=1

LOG="outputs/status/ready_tests_metrics3.log"
echo "[$(date -Iseconds)] Starting tests/metrics for E7/E8 API files" | tee "$LOG"

files=(
  "e7_deepseek-v4-flash_dense.jsonl"
  "e8_LongCat-2.0_distractor_weak.jsonl"
  "e8_LongCat-2.0_distractor_strong.jsonl"
  "e8_deepseek-v4-flash_distractor_weak.jsonl"
  "e8_deepseek-v4-flash_distractor_strong.jsonl"
)

for fname in "${files[@]}"; do
  raw="outputs/raw_generations/$fname"
  test="outputs/test_results/${fname%.jsonl}_results.jsonl"
  metric="outputs/metrics/${fname%.jsonl}_metrics.jsonl"
  [ ! -f "$raw" ] && continue
  if [ ! -f "$test" ]; then
    echo "[$(date -Iseconds)] Testing $fname" | tee -a "$LOG"
    python scripts/run_tests.py "$raw" "$test" --tasks tasks/longcat_pilot_90.jsonl 2>&1 | tee -a "$LOG"
  fi
  if [ ! -f "$metric" ]; then
    echo "[$(date -Iseconds)] Metrics $fname" | tee -a "$LOG"
    python scripts/compute_metrics.py "$test" "$metric" 2>&1 | tee -a "$LOG"
  fi
done

echo "[$(date -Iseconds)] Finished" | tee -a "$LOG"
