#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ../.venv/bin/activate 2>/dev/null || true
export PYTHONUNBUFFERED=1

LOG="outputs/status/final_validation.log"
echo "[$(date -Iseconds)] Starting final validation" | tee "$LOG"

# Validate main experiments
validate () {
  local raw=$1
  local test=$2
  local ntasks=$3
  local nconds=$4
  local nsamples=$5
  local strategy=${6:-standard}
  if [ -f "$raw" ] && [ -f "$test" ]; then
    echo "[$(date -Iseconds)] Validate $raw" | tee -a "$LOG"
    python scripts/validate_experiment_jsonl.py \
      --raw "$raw" --tested "$test" \
      --expected-tasks "$ntasks" --expected-conditions "$nconds" --expected-samples "$nsamples" \
      --expected-strategy "$strategy" 2>&1 | tee -a "$LOG"
  else
    echo "[$(date -Iseconds)] SKIP $raw (missing)" | tee -a "$LOG"
  fi
}

# E1 main
for m in qwen_3b qwen_7b codellama_7b_instruct_q5_k_m deepseek_v4_flash_main longcat_2_0_main; do
  validate "outputs/raw_generations/${m}.jsonl" "outputs/test_results/${m}_results.jsonl" 450 4 1
done

# E2 top-k
for m in qwen3b qwen7b codellama deepseek_v4_flash longcat_2_0; do
  validate "outputs/raw_generations/${m}_naive_topk_full.jsonl" "outputs/test_results/${m}_naive_topk_full_results.jsonl" 450 4 1
done

# E3a gold-reminder
for m in qwen3b qwen7b codellama deepseek_v4_flash longcat_2_0; do
  validate "outputs/raw_generations/${m}_gold_reminder_full.jsonl" "outputs/test_results/${m}_gold_reminder_full_results.jsonl" 450 2 1
done

# E3b distractor-reminder
for m in qwen3b qwen7b codellama deepseek_v4_flash longcat_2_0; do
  validate "outputs/raw_generations/${m}_distractor_reminder_full.jsonl" "outputs/test_results/${m}_distractor_reminder_full_results.jsonl" 450 2 1
done

# E4 Pass@3
for m in p1_qwen3b_n3 p1_qwen7b_n3 p1_codellama_n3 p1_deepseek_v4_flash_n3 p1_longcat_2_0_n3; do
  validate "outputs/raw_generations/${m}.jsonl" "outputs/test_results/${m}_results.jsonl" 450 4 3
done

# E5 CoT
for m in p0_qwen3b_cot p0_qwen7b_cot p0_codellama_cot p0_deepseek_v4_flash_cot p0_longcat_2_0_cot; do
  validate "outputs/raw_generations/${m}.jsonl" "outputs/test_results/${m}_results.jsonl" 450 3 1 cot
done

# E7/E8 pilot
# Local model files contain both conditions; API split files contain one condition each.
for base in e7_qwen3b e7_qwen7b e7_codellama e8_qwen3b e8_qwen7b e8_codellama; do
  validate "outputs/raw_generations/${base}.jsonl" "outputs/test_results/${base}_results.jsonl" 90 2 1
done
for base in e7_LongCat-2.0_dense e7_LongCat-2.0_hybrid e7_deepseek-v4-flash_dense e7_deepseek-v4-flash_hybrid e8_LongCat-2.0_distractor_weak e8_LongCat-2.0_distractor_strong e8_deepseek-v4-flash_distractor_weak e8_deepseek-v4-flash_distractor_strong; do
  validate "outputs/raw_generations/${base}.jsonl" "outputs/test_results/${base}_results.jsonl" 90 1 1
done

# E9 real-world
for m in e9_longcat_2_0_async e9_deepseek_v4_flash_async e9_qwen3b e9_qwen7b e9_codellama; do
  validate "realworld/outputs/raw_generations/${m}.jsonl" "realworld/outputs/test_results/${m}_results.jsonl" 90 4 1
done

echo "[$(date -Iseconds)] Final validation finished" | tee -a "$LOG"
