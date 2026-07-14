#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ../.venv/bin/activate 2>/dev/null || true
export PYTHONUNBUFFERED=1

LOG="outputs/status/ready_tests_metrics.log"
echo "[$(date -Iseconds)] Starting tests/metrics for ready files" | tee "$LOG"

files=(
  "longcat_2_0_gold_reminder_full.jsonl"
  "longcat_2_0_distractor_reminder_full.jsonl"
  "deepseek_v4_flash_gold_reminder_full.jsonl"
  "e7_LongCat-2.0_dense.jsonl"
  "e7_LongCat-2.0_hybrid.jsonl"
  "e7_deepseek-v4-flash_dense.jsonl"
)

for fname in "${files[@]}"; do
  raw="outputs/raw_generations/$fname"
  test="outputs/test_results/${fname%.jsonl}_results.jsonl"
  metric="outputs/metrics/${fname%.jsonl}_metrics.jsonl"
  if [ ! -f "$raw" ]; then
    continue
  fi
  if [ ! -f "$test" ]; then
    echo "[$(date -Iseconds)] Testing $fname" | tee -a "$LOG"
    python scripts/run_tests.py "$raw" "$test" 2>&1 | tee -a "$LOG"
  fi
  if [ ! -f "$metric" ]; then
    echo "[$(date -Iseconds)] Metrics $fname" | tee -a "$LOG"
    python scripts/compute_metrics.py "$test" "$metric" 2>&1 | tee -a "$LOG"
  fi
done

echo "[$(date -Iseconds)] Ready tests/metrics finished" | tee -a "$LOG"
