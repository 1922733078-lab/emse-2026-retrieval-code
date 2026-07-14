#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ../.venv/bin/activate 2>/dev/null || true
export PYTHONUNBUFFERED=1
export HF_ENDPOINT=https://hf-mirror.com

LOG="outputs/status/e7_e8_api.log"
echo "[$(date -Iseconds)] Starting E7/E8 API experiments" | tee "$LOG"

# E7 retrieval robustness (LongCat + DeepSeek)
for model in LongCat-2.0 deepseek-v4-flash; do
  api=longcat
  max_tokens=1024
  if [ "$model" = "deepseek-v4-flash" ]; then
    api=deepseek
    max_tokens=8192
  fi
  for cond in dense hybrid; do
    out="e7_${model/ /_}_${cond}.jsonl"
    python scripts/run_generation_api_async.py \
      --model "$model" --api "$api" \
      --tasks tasks/longcat_pilot_90.jsonl \
      --conditions "$cond" \
      --output "$out" \
      --temperature 0.0 --top-p 1.0 --max-tokens "$max_tokens" \
      --thinking disabled --strategy standard --num-samples 1 \
      --concurrency 4 --resume 2>&1 | tee -a "$LOG"
  done
done

# E8 distractor intensity (LongCat + DeepSeek)
for model in LongCat-2.0 deepseek-v4-flash; do
  api=longcat
  max_tokens=1024
  if [ "$model" = "deepseek-v4-flash" ]; then
    api=deepseek
    max_tokens=8192
  fi
  for cond in distractor_weak distractor_strong; do
    out="e8_${model/ /_}_${cond}.jsonl"
    python scripts/run_generation_api_async.py \
      --model "$model" --api "$api" \
      --tasks tasks/longcat_pilot_90.jsonl \
      --conditions "$cond" \
      --output "$out" \
      --temperature 0.0 --top-p 1.0 --max-tokens "$max_tokens" \
      --thinking disabled --strategy standard --num-samples 1 \
      --concurrency 4 --resume 2>&1 | tee -a "$LOG"
  done
done

echo "[$(date -Iseconds)] E7/E8 API experiments finished" | tee -a "$LOG"
