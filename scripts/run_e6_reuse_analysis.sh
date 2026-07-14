#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ../.venv/bin/activate 2>/dev/null || true
export PYTHONUNBUFFERED=1

LOG="outputs/status/e6_reuse_analysis.log"
echo "[$(date -Iseconds)] Starting E6 reuse mechanism analysis" | tee "$LOG"

# Combine raw and test results for E1/E3/E4 products across five models.
python3 - <<'PY' 2>&1 | tee -a "$LOG"
from pathlib import Path
import json

ROOT = Path(".")
raw_out = ROOT / "outputs" / "raw_generations" / "e6_combined_raw.jsonl"
test_out = ROOT / "outputs" / "raw_generations" / "e6_combined_test.jsonl"

files = [
    ("qwen_3b", "no naive gold distractor"),
    ("qwen_7b", "no naive gold distractor"),
    ("codellama_7b_instruct_q5_k_m", "no naive gold distractor"),
    ("deepseek_v4_flash_main", "no naive gold distractor"),
    ("longcat_2_0_main", "no naive gold distractor"),
    ("qwen3b_distractor_reminder_full", "distractor_reminder_mild distractor_reminder_strong"),
    ("qwen7b_distractor_reminder_full", "distractor_reminder_mild distractor_reminder_strong"),
    ("codellama_distractor_reminder_full", "distractor_reminder_mild distractor_reminder_strong"),
    ("deepseek_v4_flash_distractor_reminder_full", "distractor_reminder_mild distractor_reminder_strong"),
    ("longcat_2_0_distractor_reminder_full", "distractor_reminder_mild distractor_reminder_strong"),
    ("p1_qwen3b_n3", "no naive gold distractor"),
    ("p1_qwen7b_n3", "no naive gold distractor"),
    ("p1_codellama_n3", "no naive gold distractor"),
    ("p1_deepseek_v4_flash_n3", "no naive gold distractor"),
    ("p1_longcat_2_0_n3", "no naive gold distractor"),
]

raw_count = 0
test_count = 0
with raw_out.open("w") as fraw, test_out.open("w") as ftest:
    for base, conds in files:
        raw_path = ROOT / "outputs" / "raw_generations" / f"{base}.jsonl"
        test_path = ROOT / "outputs" / "test_results" / f"{base}_results.jsonl"
        if not raw_path.exists() or not test_path.exists():
            print(f"SKIP {base}: missing raw or test")
            continue
        with raw_path.open() as f:
            for line in f:
                fraw.write(line)
                raw_count += 1
        with test_path.open() as f:
            for line in f:
                ftest.write(line)
                test_count += 1
        print(f"ADD {base}: raw ok, test ok")

print(f"Combined {raw_count} raw and {test_count} test records")
print(f"Wrote {raw_out} and {test_out}")
PY

python3 scripts/analyze_reuse_mechanism.py \
  outputs/raw_generations/e6_combined_raw.jsonl \
  outputs/raw_generations/e6_combined_test.jsonl \
  results 2>&1 | tee -a "$LOG"

echo "[$(date -Iseconds)] E6 reuse mechanism analysis finished" | tee -a "$LOG"
