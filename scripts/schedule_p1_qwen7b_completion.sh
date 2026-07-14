#!/usr/bin/env bash
# Finish P1 qwen7b: run tests and compute Pass@k after generation completes.
set -uo pipefail

cd "$(dirname "$0")/.."

RAW="outputs/raw_generations/p1_qwen7b_n3.jsonl"
RESULTS="outputs/test_results/p1_qwen7b_n3_results.jsonl"

echo "[$(date)] Waiting for P1 qwen7b raw generation to complete: ${RAW}"
while [ "$(wc -l < "${RAW}")" -lt 5400 ]; do
    sleep 60
done

echo "[$(date)] P1 qwen7b generation complete. Running tests."
python scripts/run_tests.py "${RAW}" "${RESULTS}" > outputs/p1_qwen7b_test.log 2>&1

echo "[$(date)] Computing P1 qwen7b Pass@k."
python scripts/compute_passatk.py "${RESULTS}" --max-k 3 --by-level >> outputs/p1_qwen7b_test.log 2>&1

echo "[$(date)] P1 qwen7b evaluation complete."
