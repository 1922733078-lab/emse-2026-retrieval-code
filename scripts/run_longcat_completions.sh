#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ../.venv/bin/activate 2>/dev/null || true
export PYTHONUNBUFFERED=1

LOG="outputs/status/longcat_completions.log"
echo "[$(date -Iseconds)] Starting LongCat completions" | tee "$LOG"

# E3a gold-reminder
python scripts/run_generation_api_async.py \
  --model LongCat-2.0 --api longcat \
  --tasks tasks/all_tasks.jsonl \
  --conditions gold_reminder_mild gold_reminder_strong \
  --output longcat_2_0_gold_reminder_full.jsonl \
  --temperature 0.0 --top-p 1.0 --max-tokens 1024 \
  --thinking disabled --strategy standard --num-samples 1 \
  --concurrency 4 --resume 2>&1 | tee -a "$LOG"

# E3b distractor-reminder
python scripts/run_generation_api_async.py \
  --model LongCat-2.0 --api longcat \
  --tasks tasks/all_tasks.jsonl \
  --conditions distractor_reminder_mild distractor_reminder_strong \
  --output longcat_2_0_distractor_reminder_full.jsonl \
  --temperature 0.0 --top-p 1.0 --max-tokens 1024 \
  --thinking disabled --strategy standard --num-samples 1 \
  --concurrency 4 --resume 2>&1 | tee -a "$LOG"

# E5 CoT
python scripts/run_generation_api_async.py \
  --model LongCat-2.0 --api longcat \
  --tasks tasks/all_tasks.jsonl \
  --conditions no gold distractor \
  --output p0_longcat_2_0_cot.jsonl \
  --temperature 0.0 --top-p 1.0 --max-tokens 1024 \
  --thinking disabled --strategy cot --num-samples 1 \
  --concurrency 4 --resume 2>&1 | tee -a "$LOG"

# E4 Pass@3
python scripts/run_generation_api_async.py \
  --model LongCat-2.0 --api longcat \
  --tasks tasks/all_tasks.jsonl \
  --conditions no naive gold distractor \
  --output p1_longcat_2_0_n3.jsonl \
  --temperature 0.7 --top-p 1.0 --max-tokens 1024 \
  --thinking disabled --strategy standard --num-samples 3 --seed 42 \
  --concurrency 4 --resume 2>&1 | tee -a "$LOG"

echo "[$(date -Iseconds)] LongCat completions finished" | tee -a "$LOG"
