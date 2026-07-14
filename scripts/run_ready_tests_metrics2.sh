#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ../.venv/bin/activate 2>/dev/null || true
export PYTHONUNBUFFERED=1

LOG="outputs/status/ready_tests_metrics2.log"
echo "[$(date -Iseconds)] Starting tests/metrics for newly ready files" | tee "$LOG"

files=(
  "deepseek_v4_flash_distractor_reminder_full.jsonl"
  "e7_deepseek-v4-flash_hybrid.jsonl"
)

for fname in "${files[@]}"; do
  raw="outputs/raw_generations/$fname"
  test="outputs/test_results/${fname%.jsonl}_results.jsonl"
  metric="outputs/metrics/${fname%.jsonl}_metrics.jsonl"
  [ ! -f "$raw" ] && continue
  if [ ! -f "$test" ]; then
    echo "[$(date -Iseconds)] Testing $fname" | tee -a "$LOG"
    python scripts/run_tests.py "$raw" "$test" 2>&1 | tee -a "$LOG"
  fi
  if [ ! -f "$metric" ]; then
    echo "[$(date -Iseconds)] Metrics $fname" | tee -a "$LOG"
    python scripts/compute_metrics.py "$test" "$metric" 2>&1 | tee -a "$LOG"
  fi
done

echo "[$(date -Iseconds)] Finished" | tee -a "$LOG"
