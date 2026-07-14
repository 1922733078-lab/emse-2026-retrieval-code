# Reproduction Package

## Quick Start

```bash
# From this artifact root directory:
bash reproduction/reproduce_results.sh

# Verify output:
python reproduction/verify_release.py \
  --artifact-root . \
  --candidate-root reproduction/work/output
```

## What Gets Reproduced

| Artifact | Source | Method |
|---|---|---|
| `results/tables/pass_at_1_final_five.csv` | Frozen test_results JSONL | Deterministic recomputation |
| `results/tables/statistical_tests_clean.csv` | Frozen metrics JSONL | Bootstrap CI (RNG-dependent) |
| `figures/figure_1_monochrome_conditions.png/.pdf` | Pass@1 CSV | Matplotlib (Times New Roman, 600 dpi) |
| `figures/figure_2_monochrome_paired_effects.png/.pdf` | Pass@1 CSV | Matplotlib (Times New Roman, 600 dpi) |

## Expected Outputs

See `reproduction/expected_outputs.json` for row counts, column names, and SHA-256
hashes of the frozen baselines.

## Dependencies

- Python 3.12
- Times New Roman font (system font required for pixel-level reproducibility)
- All Python dependencies pinned in `requirements-lock.txt` (with hashes)

## Known Limitations

- **Bootstrap CIs**: The statistical tests table contains bootstrap confidence
  intervals that depend on NumPy's random number generator. Different NumPy
  versions may produce slightly different values (within sampling error). The
  frozen baseline is preserved as the canonical artifact.
- **Figure pixel-level reproducibility**: PNG/PDF bytes depend on Matplotlib
  version and Times New Roman font file. Data-level reproducibility is
  guaranteed via the input CSV; exact pixel reproduction requires the same
  Matplotlib version and font file.
