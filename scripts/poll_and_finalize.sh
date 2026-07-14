#!/bin/bash
set -e
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$ROOT"
LOG=outputs/final_evaluation.log
exec > "$LOG" 2>&1

echo "[$(date -Iseconds)] Monitor started."

wait_for_lines() {
  local file=$1
  local target=$2
  while true; do
    if [ -f "$file" ]; then
      local n=$(wc -l < "$file")
      if [ "$n" -ge "$target" ]; then
        echo "[$(date -Iseconds)] $file has $n lines (target $target)."
        return
      fi
    fi
    sleep 60
  done
}

# Wait for local 3B model and run its evaluation immediately.
wait_for_lines outputs/raw_generations/qwen_3b.jsonl 1800
if [ ! -f outputs/metrics/qwen_3b_metrics.jsonl ]; then
  echo "[$(date -Iseconds)] Running Qwen 3B tests and metrics."
  python scripts/run_tests.py outputs/raw_generations/qwen_3b.jsonl outputs/test_results/qwen_3b_results.jsonl
  python scripts/compute_metrics.py outputs/test_results/qwen_3b_results.jsonl outputs/metrics/qwen_3b_metrics.jsonl
  echo "[$(date -Iseconds)] Qwen 3B evaluation done."
else
  echo "[$(date -Iseconds)] Qwen 3B metrics already present; skipping."
fi

# Wait for GPT per-condition files.
for cond in no gold distractor naive; do
  wait_for_lines outputs/raw_generations/gpt_5_5_${cond}.jsonl 450
done

echo "[$(date -Iseconds)] All generation files ready."

# Run tests and metrics for GPT conditions.
for cond in no gold distractor naive; do
  python scripts/run_tests.py outputs/raw_generations/gpt_5_5_${cond}.jsonl outputs/test_results/gpt_5_5_${cond}_results.jsonl
  python scripts/compute_metrics.py outputs/test_results/gpt_5_5_${cond}_results.jsonl outputs/metrics/gpt_5_5_${cond}_metrics.jsonl
done

echo "[$(date -Iseconds)] All tests and metrics done."

# Final combined summary and statistical tests.
python scripts/combine_and_summarize.py final_all \
  outputs/metrics/qwen_7b_metrics.jsonl \
  outputs/metrics/qwen_3b_metrics.jsonl \
  outputs/metrics/deepseek_v4_flash_no_metrics.jsonl \
  outputs/metrics/deepseek_v4_flash_gold_metrics.jsonl \
  outputs/metrics/deepseek_v4_flash_distractor_metrics.jsonl \
  outputs/metrics/deepseek_v4_flash_naive_metrics.jsonl \
  outputs/metrics/gpt_5_5_no_metrics.jsonl \
  outputs/metrics/gpt_5_5_gold_metrics.jsonl \
  outputs/metrics/gpt_5_5_distractor_metrics.jsonl \
  outputs/metrics/gpt_5_5_naive_metrics.jsonl

python scripts/statistical_tests.py \
  outputs/metrics/qwen_7b_metrics.jsonl \
  outputs/metrics/qwen_3b_metrics.jsonl \
  outputs/metrics/deepseek_v4_flash_no_metrics.jsonl \
  outputs/metrics/deepseek_v4_flash_gold_metrics.jsonl \
  outputs/metrics/deepseek_v4_flash_distractor_metrics.jsonl \
  outputs/metrics/deepseek_v4_flash_naive_metrics.jsonl \
  outputs/metrics/gpt_5_5_no_metrics.jsonl \
  outputs/metrics/gpt_5_5_gold_metrics.jsonl \
  outputs/metrics/gpt_5_5_distractor_metrics.jsonl \
  outputs/metrics/gpt_5_5_naive_metrics.jsonl \
  --output results/tables/statistical_tests_final_all.csv

echo "[$(date -Iseconds)] Final evaluation complete."
