# Supplementary Experiment Artifacts

**Paper**: Rivalry in Retrieved Code: How Plausible Distractors Undermine Code Generation with Retrieval-Augmented Context

**Target Journal**: *Empirical Software Engineering* (EMSE)

**Final Models**:
1. Qwen2.5-Coder-3B
2. Qwen2.5-Coder-7B
3. CodeLlama-7B
4. DeepSeek-V4-Flash
5. LongCat-2.0

---

## Directory Structure

```
outputs/
├── manifests/          # Final input manifests (frozen)
├── raw_generations/    # Raw model outputs (frozen)
├── test_results/       # Test execution results (frozen)
└── metrics/            # Per-sample metrics (frozen)
results/
└── tables/             # Aggregated summary tables (frozen)
scripts/                # Analysis and reconstruction scripts
reproduction/           # Zero-cost reproduction package
    ├── reproduce_results.sh
    ├── verify_release.py
    └── work/           # Temporary working directory (excluded from release)
```

---

## Zero-Cost Result Reproduction

This package supports **zero-cost result reproduction**: recomputing the paper's
central results table and two submission figures **without invoking any model
API and without any fees**.

### Difference from API Re-generation

| Scope | Zero-Cost Reproduction | API Re-generation |
|---|---|---|
| What it does | Recompute Pass@1 and statistics from frozen test results | Re-run model inference and re-test |
| Requires API calls | No | Yes (costs money) |
| Included here | Yes | No (separate future step) |

### Requirements

- Python 3.12
- `requirements-lock.txt` (locked dependencies with SHA-256 hashes)
- Times New Roman font (system font on macOS; required for pixel-level figure reproducibility)

### One-Command Reproduction

```bash
bash reproduction/reproduce_results.sh
```

This will:
1. Verify the manifest and frozen inputs
2. Rebuild `results/tables/pass_at_1_final_five.csv`
3. Rebuild `results/tables/statistical_tests_clean.csv`
4. Rebuild Figure 1 and Figure 2 (PNG 600 dpi + PDF)
5. Verify output against frozen baselines

### Output Location

- Tables: `reproduction/work/output/results/tables/`
- Figures: `reproduction/work/output/figures/`

### Verification

```bash
python reproduction/verify_release.py \
  --artifact-root . \
  --candidate-root reproduction/work/output
```

---

## Data Availability

**Status**: DOI pending archival release. Once a DOI is obtained, this section will
be updated. Raw model outputs are subject to provider terms and will not be
publicly released without confirmation of redistribution rights.

---

## Model Output Availability

Model API outputs are archived but public release requires confirmation of
redistribution rights from each model provider. The frozen test results (pass/fail
per task) are sufficient to reproduce all paper tables and figures.

---

## Citation

If you use these artifacts, please cite the forthcoming paper:

> Rivalry in Retrieved Code: How Plausible Distractors Undermine Code Generation
> with Retrieval-Augmented Context. Target journal: *Empirical Software Engineering*.

DOI pending.

---

## Contact

For questions about reproduction or data access, please contact the authors.

---

**Note**: This README will be finalized upon DOI assignment. No fictional DOIs are
used.
