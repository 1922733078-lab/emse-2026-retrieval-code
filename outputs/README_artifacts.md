# Supplementary Experiment Artifacts — LongCat-2.0 Five-Model Study

This directory contains the complete experimental artifacts for the
LongCat-2.0 replacement and five-model supplementary study described in
`LongCat-2.0替换与六模型完整实验执行手册.md`.

## Reproduction Environment

- Python 3.12
- Dependencies: see `requirements-lock.txt` (to be generated)
- GPU: NVIDIA RTX 4090 (24 GB) for local models
- API access: DeepSeek-V4-Flash, LongCat-2.0

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API keys in .env
cp .env.example .env
# edit .env

# 3. Run smoke test
python scripts/run_generation_api_async.py \
  --model LongCat-2.0 --api longcat \
  --tasks tasks/longcat_pilot_90.jsonl \
  --conditions no gold \
  --output longcat_2_0_smoke.jsonl \
  --temperature 0.0 --top-p 1.0 --max-tokens 1024 \
  --thinking disabled --strategy standard --num-samples 1 \
  --concurrency 4 --limit 2

# 4. Run tests and compute metrics
python scripts/run_tests.py outputs/raw_generations/EXPERIMENT.jsonl outputs/test_results/EXPERIMENT_results.jsonl
python scripts/compute_metrics.py outputs/test_results/EXPERIMENT_results.jsonl outputs/metrics/EXPERIMENT_metrics.jsonl

# 5. Validate
python scripts/validate_experiment_jsonl.py \
  --raw outputs/raw_generations/EXPERIMENT.jsonl \
  --tested outputs/test_results/EXPERIMENT_results.jsonl \
  --expected-tasks 450 --expected-conditions 4 --expected-samples 1
```

## Directory Layout

```
outputs/raw_generations/   # Raw model generations (JSONL)
outputs/test_results/      # Test execution results (JSONL)
outputs/metrics/           # Similarity/citation/error metrics (JSONL)
outputs/manifests/         # Run manifests and final input list
outputs/status/            # Execution logs and progress reports
outputs/errors/            # Failed API requests (retried then closed)
results/tables/            # Aggregated CSV tables
results/figures/           # PDF/PNG figures
retrieval_contexts/        # Retrieval snippets for all conditions
tasks/                     # Task definitions
prompts/                   # Prompt templates
scripts/                   # Runner and analysis scripts
realworld/                 # E9 real-world repo manifest and task framework
libs/                      # Synthetic library implementations
solutions/                 # Reference solutions for synthetic tasks
```

## Experiment Matrix

| Experiment | Conditions | Models | Records per model |
|---|---|---|---|
| E1 Main | no, naive, gold, distractor | 5 | 1,800 |
| E2 top-k | naive_topk_1/3/5/10 | 5 | 1,800 |
| E3a gold-reminder | gold_reminder_mild/strong | 5 | 900 |
| E3b distractor-reminder | distractor_reminder_mild/strong | 5 | 900 |
| E4 Pass@3 | no, naive, gold, distractor × 3 samples | 5 | 5,400 |
| E5 CoT | no, gold, distractor (cot strategy) | 5 | 1,350 |
| E6 Reuse mechanism | derived from E1/E3/E4 | 5 | - |
| E7 Retriever robustness | dense, hybrid (pilot 90 tasks) | 5 | 180 |
| E8 Distractor intensity | distractor_weak, distractor_strong (pilot) | 5 | 180 |
| E9 Real-world validation | no, naive, gold, distractor (framework) | 5 | - |

## Notes

- GPT-5.5 and MiniMax-M2.5 raw data are retained under
  `outputs/raw_generations/` for audit but are excluded from the final
  manifest `outputs/manifests/final_five_model_inputs.json`.
- LongCat standard experiments use `thinking=disabled` via
  `extra_body={"thinking":{"type":"disabled"}}`.
- API costs are logged in each experiment's status log.

## Contact / Data Availability

See the main paper `Statements and Declarations` section for data and code
availability.
