#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ../.venv/bin/activate 2>/dev/null || true
export PYTHONUNBUFFERED=1
export CUDA_VISIBLE_DEVICES=0

LOG="outputs/status/local_completions.log"
echo "[$(date -Iseconds)] Starting local model completions" | tee "$LOG"

run_local () {
  local model=$1
  local conds=$2
  local out=$3
  local tasks=${4:-tasks/all_tasks.jsonl}
  if [ -f "outputs/raw_generations/$out" ]; then
    echo "[$(date -Iseconds)] Resuming $model $conds -> $out" | tee -a "$LOG"
    python scripts/run_generation.py \
      --model "$model" \
      --tasks "$tasks" \
      --conditions $conds \
      --output "$out" \
      --temperature 0.0 --top-p 1.0 --max-tokens 1024 \
      --strategy standard --num-samples 1 \
      --resume 2>&1 | tee -a "$LOG"
  else
    echo "[$(date -Iseconds)] Starting $model $conds -> $out" | tee -a "$LOG"
    python scripts/run_generation.py \
      --model "$model" \
      --tasks "$tasks" \
      --conditions $conds \
      --output "$out" \
      --temperature 0.0 --top-p 1.0 --max-tokens 1024 \
      --strategy standard --num-samples 1 2>&1 | tee -a "$LOG"
  fi
}

# E3b distractor-reminder
run_local qwen3b "distractor_reminder_mild distractor_reminder_strong" qwen3b_distractor_reminder_full.jsonl
run_local qwen7b "distractor_reminder_mild distractor_reminder_strong" qwen7b_distractor_reminder_full.jsonl
run_local codellama "distractor_reminder_mild distractor_reminder_strong" codellama_distractor_reminder_full.jsonl

# E3a gold-reminder
run_local qwen3b "gold_reminder_mild gold_reminder_strong" qwen3b_gold_reminder_full.jsonl
run_local qwen7b "gold_reminder_mild gold_reminder_strong" qwen7b_gold_reminder_full.jsonl
run_local codellama "gold_reminder_mild gold_reminder_strong" codellama_gold_reminder_full.jsonl

# E7 retrieval robustness (pilot tasks)
run_local qwen3b "dense hybrid" e7_qwen3b.jsonl tasks/longcat_pilot_90.jsonl
run_local qwen7b "dense hybrid" e7_qwen7b.jsonl tasks/longcat_pilot_90.jsonl
run_local codellama "dense hybrid" e7_codellama.jsonl tasks/longcat_pilot_90.jsonl

# E8 distractor intensity (pilot tasks)
run_local qwen3b "distractor_weak distractor_strong" e8_qwen3b.jsonl tasks/longcat_pilot_90.jsonl
run_local qwen7b "distractor_weak distractor_strong" e8_qwen7b.jsonl tasks/longcat_pilot_90.jsonl
run_local codellama "distractor_weak distractor_strong" e8_codellama.jsonl tasks/longcat_pilot_90.jsonl

echo "[$(date -Iseconds)] Local model completions finished" | tee -a "$LOG"

# Trigger post-processing and E6 after local work finishes.
echo "[$(date -Iseconds)] Running post-generation pipeline" | tee -a "$LOG"
bash scripts/run_post_generation_pipeline.sh 2>&1 | tee -a "$LOG"

echo "[$(date -Iseconds)] Running E6 reuse analysis" | tee -a "$LOG"
bash scripts/run_e6_reuse_analysis.sh 2>&1 | tee -a "$LOG"

echo "[$(date -Iseconds)] Building final manifest" | tee -a "$LOG"
python3 scripts/build_final_manifest.py 2>&1 | tee -a "$LOG"

echo "[$(date -Iseconds)] All local work complete" | tee -a "$LOG"
