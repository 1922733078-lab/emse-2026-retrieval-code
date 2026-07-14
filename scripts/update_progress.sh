#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
from pathlib import Path
import json, datetime, re

raw_dir = Path("outputs/raw_generations")
status_dir = Path("outputs/status")
status_dir.mkdir(parents=True, exist_ok=True)

targets = {
    "longcat_gold_reminder": ("longcat_2_0_gold_reminder_full.jsonl", 900),
    "longcat_distractor_reminder": ("longcat_2_0_distractor_reminder_full.jsonl", 900),
    "longcat_cot": ("p0_longcat_2_0_cot.jsonl", 1350),
    "longcat_pass3": ("p1_longcat_2_0_n3.jsonl", 5400),
    "deepseek_gold_reminder": ("deepseek_v4_flash_gold_reminder_full.jsonl", 900),
    "deepseek_distractor_reminder": ("deepseek_v4_flash_distractor_reminder_full.jsonl", 900),
    "qwen3b_distractor_reminder": ("qwen3b_distractor_reminder_full.jsonl", 900),
    "qwen7b_distractor_reminder": ("qwen7b_distractor_reminder_full.jsonl", 900),
    "codellama_distractor_reminder": ("codellama_distractor_reminder_full.jsonl", 900),
    "qwen3b_gold_reminder": ("qwen3b_gold_reminder_full.jsonl", 900),
    "qwen7b_gold_reminder": ("qwen7b_gold_reminder_full.jsonl", 900),
    "codellama_gold_reminder": ("codellama_gold_reminder_full.jsonl", 900),
}

lines = []
lines.append(f"[{datetime.datetime.now().isoformat()}] Progress update")
total_done = 0
total_target = 0
for name, (fname, target) in targets.items():
    p = raw_dir / fname
    n = 0
    if p.exists():
        with open(p) as f:
            n = sum(1 for _ in f)
    pct = n / target * 100
    lines.append(f"  {name:30s}: {n:5d}/{target:5d} ({pct:5.1f}%)")
    total_done += n
    total_target += target

lines.append(f"  {'TOTAL':30s}: {total_done:5d}/{total_target:5d} ({total_done/total_target*100:5.1f}%)")

# Check running processes
import subprocess
try:
    procs = subprocess.check_output(["ps", "aux"], text=True)
    running = []
    for key in ["longcat", "deepseek", "run_generation.py"]:
        if key in procs:
            running.append(key)
    lines.append(f"  Running processes: {', '.join(running) if running else 'none'}")
except Exception:
    pass

out = "\n".join(lines) + "\n"
with open(status_dir / "overall.log", "w") as f:
    f.write(out)
print(out)
PY
