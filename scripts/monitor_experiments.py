"""Monitor running supplementary experiments and append a status snapshot."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "outputs"


def run_cmd(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception as e:
        return f"error: {e}"


def count_lines(path: Path) -> int:
    try:
        with path.open(encoding="utf-8") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def tail(path: Path, n: int = 3) -> str:
    try:
        with path.open(encoding="utf-8") as f:
            lines = f.readlines()
            return "".join(lines[-n:]).strip()
    except Exception:
        return "N/A"


def main() -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    gpu = run_cmd(["nvidia-smi", "--query-gpu=memory.used,memory.total,memory.free,utilization.gpu", "--format=csv,nounits,noheader"])

    snapshot = []
    snapshot.append(f"\n{'='*60}")
    snapshot.append(f"Snapshot: {now}")
    snapshot.append(f"GPU (used/total/free/util%): {gpu}")
    snapshot.append("-" * 60)

    experiments = [
        # Phase C six-model synthesis
        ("MiniMax main", "minimax_m25_main.jsonl", "minimax_main_gen.log", 1800),
        ("MiniMax gold-reminder", "minimax_m25_gold_reminder_full.jsonl", "minimax_gold_reminder_gen.log", 900),
        ("MiniMax distractor-reminder", "minimax_m25_distractor_reminder_full.jsonl", "minimax_distractor_reminder_gen.log", 900),
        ("MiniMax Pass@3", "p1_minimax_m25_n3.jsonl", "minimax_passatk_gen.log", 5400),
        ("MiniMax CoT", "p0_minimax_m25_cot.jsonl", "minimax_cot_gen.log", 1350),
        ("LongCat gold-reminder", "longcat_2_0_gold_reminder_full.jsonl", "longcat_gold_reminder_gen.log", 900),
        ("LongCat distractor-reminder", "longcat_2_0_distractor_reminder_full.jsonl", "longcat_distractor_reminder_gen.log", 900),
        ("LongCat Pass@3", "p1_longcat_2_0_n3.jsonl", "longcat_passatk_gen.log", 5400),
        ("LongCat CoT", "p0_longcat_2_0_cot.jsonl", "longcat_cot_gen.log", 1350),
        ("DeepSeek gold-reminder", "deepseek_v4_flash_gold_reminder_full.jsonl", "deepseek_gold_reminder_gen.log", 900),
        ("DeepSeek distractor-reminder", "deepseek_v4_flash_distractor_reminder_full.jsonl", "deepseek_distractor_reminder_gen.log", 900),
        ("qwen3b distractor-reminder", "qwen3b_distractor_reminder_full.jsonl", "qwen3b_distractor_reminder_gen.log", 900),
        # Existing supplementary experiments
        ("P1 qwen3b Pass@3", "p1_qwen3b_n3.jsonl", "p1_qwen3b.log", 5400),
        ("P1 qwen7b Pass@3", "p1_qwen7b_n3.jsonl", "p1_qwen7b.log", 5400),
        ("P1 codellama Pass@3", "p1_codellama_n3.jsonl", "p1_codellama.log", 5400),
        ("P1 deepseek Pass@3", "p1_deepseek_v4_flash_n3.jsonl", "p1_deepseek_v4_flash.log", 5400),
        ("P0 codellama CoT", "p0_codellama_cot.jsonl", "p0_codellama.log", 1350),
        ("P0 qwen3b CoT", "p0_qwen3b_cot.jsonl", "p0_qwen3b.log", 1350),
        ("P0 qwen7b CoT", "p0_qwen7b_cot.jsonl", "p0_qwen7b.log", 1350),
        ("P0 deepseek CoT", "p0_deepseek_v4_flash_cot.jsonl", "p0_deepseek_v4_flash.log", 1350),
    ]

    for name, raw_file, log_file, total in experiments:
        raw_path = OUTPUT_DIR / "raw_generations" / raw_file
        log_path = OUTPUT_DIR / log_file
        if raw_path.exists():
            done = count_lines(raw_path)
            pct = done / total * 100
            last = tail(log_path, 2)
            snapshot.append(f"{name}: {done}/{total} ({pct:.1f}%)")
            snapshot.append(f"  last log: {last.replace(chr(10), ' | ')}")
        else:
            snapshot.append(f"{name}: not started")

    snapshot.append("=" * 60)

    log_path = OUTPUT_DIR / "experiment_monitor.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(snapshot) + "\n")

    print("\n".join(snapshot))


if __name__ == "__main__":
    main()
