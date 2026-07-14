#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ../.venv/bin/activate 2>/dev/null || true
export PYTHONUNBUFFERED=1

LOG="outputs/status/post_generation.log"
echo "[$(date -Iseconds)] Starting post-generation pipeline" | tee "$LOG"

# Final raw/test/metric files for the five-model matrix
matrix_files=(
  # E1 main
  "qwen_3b"
  "qwen_7b"
  "codellama_7b_instruct_q5_k_m"
  "deepseek_v4_flash_main"
  "longcat_2_0_main"
  # E2 top-k
  "qwen3b_naive_topk_full"
  "qwen7b_naive_topk_full"
  "codellama_naive_topk_full"
  "deepseek_v4_flash_naive_topk_full"
  "longcat_2_0_naive_topk_full"
  # E3a gold-reminder
  "qwen3b_gold_reminder_full"
  "qwen7b_gold_reminder_full"
  "codellama_gold_reminder_full"
  "deepseek_v4_flash_gold_reminder_full"
  "longcat_2_0_gold_reminder_full"
  # E3b distractor-reminder
  "qwen3b_distractor_reminder_full"
  "qwen7b_distractor_reminder_full"
  "codellama_distractor_reminder_full"
  "deepseek_v4_flash_distractor_reminder_full"
  "longcat_2_0_distractor_reminder_full"
  # E4 Pass@3
  "p1_qwen3b_n3"
  "p1_qwen7b_n3"
  "p1_codellama_n3"
  "p1_deepseek_v4_flash_n3"
  "p1_longcat_2_0_n3"
  # E5 CoT
  "p0_qwen3b_cot"
  "p0_qwen7b_cot"
  "p0_codellama_cot"
  "p0_deepseek_v4_flash_cot"
  "p0_longcat_2_0_cot"
  # E7 retrieval robustness
  "e7_qwen3b"
  "e7_qwen7b"
  "e7_codellama"
  "e7_LongCat-2.0_dense"
  "e7_LongCat-2.0_hybrid"
  "e7_deepseek-v4-flash_dense"
  "e7_deepseek-v4-flash_hybrid"
  # E8 distractor intensity
  "e8_qwen3b"
  "e8_qwen7b"
  "e8_codellama"
  "e8_LongCat-2.0_distractor_weak"
  "e8_LongCat-2.0_distractor_strong"
  "e8_deepseek-v4-flash_distractor_weak"
  "e8_deepseek-v4-flash_distractor_strong"
)

for base in "${matrix_files[@]}"; do
  raw="outputs/raw_generations/${base}.jsonl"
  test="outputs/test_results/${base}_results.jsonl"
  metric="outputs/metrics/${base}_metrics.jsonl"
  if [ ! -f "$raw" ]; then
    echo "[$(date -Iseconds)] SKIP $base: raw missing" | tee -a "$LOG"
    continue
  fi
  if [ ! -f "$test" ]; then
    echo "[$(date -Iseconds)] TEST $base" | tee -a "$LOG"
    python scripts/run_tests.py "$raw" "$test" 2>&1 | tee -a "$LOG"
  fi
  if [ ! -f "$metric" ]; then
    echo "[$(date -Iseconds)] METRIC $base" | tee -a "$LOG"
    python scripts/compute_metrics.py "$test" "$metric" 2>&1 | tee -a "$LOG"
  fi
done

echo "[$(date -Iseconds)] Post-generation pipeline finished" | tee -a "$LOG"
