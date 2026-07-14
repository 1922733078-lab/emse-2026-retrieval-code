#!/usr/bin/env bash
# Combined runner: full P1 Pass@k followed by P0 CoT ablation.
# Use this to run both supplementary experiments back-to-back.
set -uo pipefail

cd "$(dirname "$0")/.."

LOG="outputs/p1_p0_combined.log"
exec > "$LOG" 2>&1

echo "============================================"
echo "Starting P1 Pass@3 experiment"
echo "============================================"
bash scripts/run_p1_passatk.sh

echo ""
echo "============================================"
echo "Starting P0 CoT ablation experiment"
echo "============================================"
bash scripts/run_p0_cot.sh

echo ""
echo "============================================"
echo "Generating final comparison tables"
echo "============================================"
python scripts/generate_supplementary_tables.py \
    outputs/test_results \
    outputs/supplementary_tables \
    > outputs/supplementary_tables.log 2>&1 || true

echo ""
echo "============================================"
echo "All supplementary experiments complete"
echo "============================================"
