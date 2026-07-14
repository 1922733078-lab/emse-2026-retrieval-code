"""Run tests and compute metrics for all raw generation JSONL files."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "outputs" / "raw_generations"
TEST_DIR = ROOT / "outputs" / "test_results"
METRICS_DIR = ROOT / "outputs" / "metrics"
TEST_DIR.mkdir(parents=True, exist_ok=True)
METRICS_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    files = sorted(RAW_DIR.glob("*.jsonl"))
    # Skip reference oracle since it is already tested.
    files = [p for p in files if "reference_oracle" not in p.name and not p.name.startswith("test_")]
    if not files:
        print(f"No generation files found in {RAW_DIR}")
        sys.exit(0)

    metrics_files = []
    for gen_path in files:
        test_path = TEST_DIR / f"{gen_path.stem}_results.jsonl"
        metrics_path = METRICS_DIR / f"{gen_path.stem}_metrics.jsonl"
        print(f"\n=== Testing {gen_path.name} -> {test_path.name} ===")
        subprocess.run([sys.executable, "scripts/run_tests.py", str(gen_path), str(test_path)], check=True)
        print(f"=== Metrics {test_path.name} -> {metrics_path.name} ===")
        subprocess.run([sys.executable, "scripts/compute_metrics.py", str(test_path), str(metrics_path)], check=True)
        metrics_files.append(metrics_path)

    # Combine all metrics into summary tables/figures.
    if len(metrics_files) >= 1:
        suffix = "all_models"
        cmd = [sys.executable, "scripts/combine_and_summarize.py", suffix] + [str(p) for p in metrics_files]
        print(f"\n=== Combining results ({suffix}) ===")
        subprocess.run(cmd, check=True)

        # Statistical tests.
        test_cmd = [sys.executable, "scripts/statistical_tests.py"] + [str(p) for p in metrics_files]
        print("=== Running statistical tests ===")
        subprocess.run(test_cmd, check=True)

    print("\nAll evaluations complete.")


if __name__ == "__main__":
    main()
