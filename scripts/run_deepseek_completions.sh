#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ../.venv/bin/activate 2>/dev/null || true
export PYTHONUNBUFFERED=1

LOG="outputs/status/deepseek_completions.log"
echo "[$(date -Iseconds)] Starting DeepSeek completions" | tee "$LOG"

# E3a gold-reminder
python scripts/run_generation_api_async.py \
  --model deepseek-v4-flash --api deepseek \
  --tasks tasks/all_tasks.jsonl \
  --conditions gold_reminder_mild gold_reminder_strong \
  --output deepseek_v4_flash_gold_reminder_full.jsonl \
  --temperature 0.0 --top-p 1.0 --max-tokens 8192 \
  --strategy standard --num-samples 1 \
  --concurrency 4 --resume 2>&1 | tee -a "$LOG"

# E3b distractor-reminder
python scripts/run_generation_api_async.py \
  --model deepseek-v4-flash --api deepseek \
  --tasks tasks/all_tasks.jsonl \
  --conditions distractor_reminder_mild distractor_reminder_strong \
  --output deepseek_v4_flash_distractor_reminder_full.jsonl \
  --temperature 0.0 --top-p 1.0 --max-tokens 8192 \
  --strategy standard --num-samples 1 \
  --concurrency 4 --resume 2>&1 | tee -a "$LOG"

echo "[$(date -Iseconds)] DeepSeek completions finished" | tee -a "$LOG"
