"""Wait for all supplementary experiments to finish, then aggregate and generate tables."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
RAW_DIR = OUTPUTS / "raw_generations"
TEST_DIR = OUTPUTS / "test_results"
TABLE_DIR = OUTPUTS / "supplementary_tables"

EXPECTED_TEST_RESULTS = [
    TEST_DIR / "p1_qwen3b_n3_results.jsonl",
    TEST_DIR / "p1_qwen7b_n3_results.jsonl",
    TEST_DIR / "p1_codellama_n3_results.jsonl",
    TEST_DIR / "p1_deepseek_v4_flash_n3_results.jsonl",
    TEST_DIR / "p0_qwen3b_cot_results.jsonl",
    TEST_DIR / "p0_qwen7b_cot_results.jsonl",
    TEST_DIR / "p0_codellama_cot_results.jsonl",
    TEST_DIR / "p0_deepseek_v4_flash_cot_results.jsonl",
]


def log(msg: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with (OUTPUTS / "finalize_supplementary.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(cmd: list[str]) -> None:
    log(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ROOT, check=True)


def all_finished() -> bool:
    return all(p.exists() and p.stat().st_size > 0 for p in EXPECTED_TEST_RESULTS)


def main() -> None:
    log("Watcher started")
    while not all_finished():
        missing = [p.name for p in EXPECTED_TEST_RESULTS if not p.exists()]
        log(f"Waiting for {len(missing)} result files: {', '.join(missing)}")
        time.sleep(300)

    log("All result files present; running final aggregation and table generation")

    # Aggregate P0 CoT results.
    p0_summary = OUTPUTS / "p0_cot_summary.csv"
    if not p0_summary.exists():
        try:
            run(
                [
                    sys.executable,
                    "scripts/compute_passatk.py",
                    str(TEST_DIR / "p0_qwen3b_cot_results.jsonl"),
                    str(TEST_DIR / "p0_qwen7b_cot_results.jsonl"),
                    str(TEST_DIR / "p0_codellama_cot_results.jsonl"),
                    str(TEST_DIR / "p0_deepseek_v4_flash_cot_results.jsonl"),
                    "--max-k",
                    "1",
                    "--output",
                    str(p0_summary),
                ]
            )
        except Exception as e:
            log(f"P0 aggregate skipped/failed: {e}")

    # Aggregate P1 Pass@k results.
    p1_summary = OUTPUTS / "p1_passatk_summary.csv"
    if not p1_summary.exists():
        try:
            run(
                [
                    sys.executable,
                    "scripts/compute_passatk.py",
                    str(TEST_DIR / "p1_qwen3b_n3_results.jsonl"),
                    str(TEST_DIR / "p1_qwen7b_n3_results.jsonl"),
                    str(TEST_DIR / "p1_codellama_n3_results.jsonl"),
                    str(TEST_DIR / "p1_deepseek_v4_flash_n3_results.jsonl"),
                    "--max-k",
                    "3",
                    "--output",
                    str(p1_summary),
                ]
            )
        except Exception as e:
            log(f"P1 aggregate skipped/failed: {e}")

    # Generate paper tables.
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        run(
            [
                sys.executable,
                "scripts/generate_supplementary_tables.py",
                str(TEST_DIR),
                str(TABLE_DIR),
            ]
        )
    except Exception as e:
        log(f"Table generation failed: {e}")
        raise

    log("Finalize complete")


if __name__ == "__main__":
    main()
