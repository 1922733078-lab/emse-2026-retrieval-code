#!/usr/bin/env bash
# reproduce_results.sh — single entry point for zero-cost reproduction.
# Recomputes the final-five-model results table, statistics, and two
# monochrome submission figures from frozen experiment outputs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$ARTIFACT_ROOT/reproduction/work/.venv-lock"
OUTPUT_ROOT="$ARTIFACT_ROOT/reproduction/work/output"
LOG_DIR="$OUTPUT_ROOT/logs"

# --- Python version check ---
PY_VERSION=$(python3.12 --version 2>&1 | awk '{print $2}')
PY_MAJOR_MINOR=$(echo "$PY_VERSION" | cut -d. -f1,2)
if [ "$PY_MAJOR_MINOR" != "3.12" ]; then
    echo "FAIL: Python 3.12 required, got $PY_VERSION" >&2
    exit 2
fi

# --- Activate venv ---
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating venv at $VENV_DIR ..."
    python3.12 -m venv "$VENV_DIR"
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    python -m pip install --quiet --upgrade pip
    python -m pip install --quiet -r "$ARTIFACT_ROOT/requirements-lock.txt"
else
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
fi

# --- Verify lock file present ---
if [ ! -f "$ARTIFACT_ROOT/requirements-lock.txt" ]; then
    echo "FAIL: requirements-lock.txt missing" >&2
    exit 2
fi
if [ ! -f "$ARTIFACT_ROOT/runtime.json" ]; then
    echo "FAIL: runtime.json missing" >&2
    exit 2
fi

# --- Check for API keys (warn only, never echo values) ---
for var in OPENAI_API_KEY DEEPSEEK_API_KEY LONGCAT_API_KEY; do
    if [ -n "${!var:-}" ]; then
        echo "WARNING: $var is set but will NOT be used by this reproduction pipeline."
    fi
done

# --- Clean previous output (never touch frozen data) ---
rm -rf "$OUTPUT_ROOT/results" "$OUTPUT_ROOT/figures" "$LOG_DIR"
mkdir -p "$OUTPUT_ROOT/results/tables" "$OUTPUT_ROOT/figures" "$LOG_DIR"

# --- Verify manifest and frozen inputs ---
echo "[1/6] Verifying manifest..."
python3 -c "
import json, sys
from pathlib import Path
mf = Path('$ARTIFACT_ROOT/outputs/manifests/final_five_model_inputs.json')
data = json.loads(mf.read_text())
assert len(data['models']) == 5, 'expected 5 models'
assert data['experiments']['E1_main'], 'E1_main missing'
assert not data['missing_raw_files'], f'missing_raw_files: {data[\"missing_raw_files\"]}'
print('manifest OK: 5 models, E1_main present, no missing files')
" 2>&1 | tee "$LOG_DIR/manifest_check.txt"

# --- Rebuild main table ---
echo "[2/6] Rebuilding final-five Pass@1 table..."
python3 "$ARTIFACT_ROOT/scripts/rebuild_final_five_tables.py" \
    --manifest "$ARTIFACT_ROOT/outputs/manifests/final_five_model_inputs.json" \
    --artifact-root "$ARTIFACT_ROOT" \
    --output-root "$OUTPUT_ROOT" \
    --seed 20260713 \
    2>&1 | tee "$LOG_DIR/rebuild_table.log"

# --- Rebuild statistics ---
echo "[3/6] Rebuilding statistical tests..."
python3 "$ARTIFACT_ROOT/scripts/rebuild_main_statistics.py" \
    --manifest "$ARTIFACT_ROOT/outputs/manifests/final_five_model_inputs.json" \
    --artifact-root "$ARTIFACT_ROOT" \
    --output-root "$OUTPUT_ROOT" \
    --seed 0 \
    2>&1 | tee "$LOG_DIR/rebuild_statistics.log" || true

# --- Check Times New Roman ---
echo "[4/6] Checking Times New Roman..."
python3 -c "
from matplotlib import font_manager
p = font_manager.findfont('Times New Roman', fallback_to_default=False)
print(f'Times New Roman found: {p}')
" 2>&1 | tee "$LOG_DIR/font_check.log"

# --- Rebuild figures ---
echo "[5/6] Rebuilding submission figures..."
python3 "$ARTIFACT_ROOT/scripts/rebuild_submission_figures.py" \
    --input-csv "$OUTPUT_ROOT/results/tables/pass_at_1_final_five.csv" \
    --output-dir "$OUTPUT_ROOT/figures" \
    2>&1 | tee "$LOG_DIR/rebuild_figures.log"

# --- Verify output vs frozen baseline ---
echo "[6/6] Verifying output..."
FROZEN_TABLE="$ARTIFACT_ROOT/results/tables/pass_at_1_final_five.csv"
CANDIDATE_TABLE="$OUTPUT_ROOT/results/tables/pass_at_1_final_five.csv"

if diff -q "$CANDIDATE_TABLE" "$FROZEN_TABLE" > /dev/null 2>&1; then
    echo "PASS: pass_at_1_final_five.csv matches frozen baseline (byte-identical)"
else
    echo "FAIL: pass_at_1_final_five.csv differs from frozen baseline" >&2
    exit 1
fi

# --- Print hash summary ---
echo ""
echo "=== REPRODUCTION HASH SUMMARY ==="
echo "Input manifest:  $(shasum -a 256 "$ARTIFACT_ROOT/outputs/manifests/final_five_model_inputs.json" | cut -d' ' -f1)"
echo "Candidate table: $(shasum -a 256 "$CANDIDATE_TABLE" | cut -d' ' -f1)"
echo "Frozen table:    $(shasum -a 256 "$FROZEN_TABLE" | cut -d' ' -f1)"
echo ""
echo "Outputs in: $OUTPUT_ROOT"
echo "Logs in: $LOG_DIR"
echo ""
echo "=== REPRODUCTION COMPLETE ==="