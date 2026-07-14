#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_NAME="supplementary_experiment_artifacts_${TIMESTAMP}.tar.gz"
OUT_DIR="/root/rivermind-data/lost+found/CCF-B/02-实验代码/retrieval-vs-reasoning"
OUT_PATH="${OUT_DIR}/${OUT_NAME}"

# Build README if not exists
README="outputs/README_artifacts.md"
if [ ! -f "$README" ]; then
  cat > "$README" <<'RM'
# Supplementary Experiment Artifacts

This archive contains the outputs and materials for the LongCat-2.0 five-model
supplementary experiments described in the execution manual.

## Contents

- `outputs/raw_generations/` – raw model generations (JSONL)
- `outputs/test_results/` – test execution results (JSONL)
- `outputs/metrics/` – similarity and citation metrics (JSONL)
- `outputs/manifests/` – run manifests and input lists
- `outputs/status/` – execution logs and progress reports
- `results/tables/` – aggregated CSV tables
- `results/figures/` – PDF/PNG figures
- `retrieval_contexts/` – gold, naive, distractor, dense, hybrid, weak/strong contexts
- `tasks/` – task definitions including pilot tasks
- `prompts/` – prompt templates
- `scripts/` – runner and analysis scripts
- `realworld/` – E9 real-world repo manifest and generated tasks (framework)

## Excluded Models

GPT-5.5 and MiniMax-M2.5 raw data are retained under `outputs/raw_generations/`
for audit but are marked `excluded_from_final_study=true` in the final manifest.
RM
fi

echo "Packaging supplementary artifacts into ${OUT_PATH}..."
tar -czf "${OUT_PATH}" \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='outputs/final_artifacts_20260630' \
  outputs/README_artifacts.md \
  outputs/raw_generations \
  outputs/test_results \
  outputs/metrics \
  outputs/manifests \
  outputs/status \
  outputs/supplementary_tables \
  results \
  retrieval_contexts \
  tasks \
  prompts \
  scripts \
  realworld \
  libs \
  solutions \
  .env.example \
  README.md

echo "Created ${OUT_PATH}"
ls -lh "${OUT_PATH}"
