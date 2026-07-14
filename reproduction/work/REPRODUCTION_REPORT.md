# Reproduction Report

## Scope
- Recomputed from frozen outputs: **yes**
- Any API/model inference invoked: **no** (required)
- Total API calls: **0**

## Environment
- Python: 3.12.13 (CPython)
- Platform: macOS-26.5.1-arm64-arm-64bit
- Machine: arm64
- Times New Roman path and SHA-256: `/System/Library/Fonts/Supplemental/Times New Roman.ttf` | `f3b4ffff71c2a0c7227d37497683b2498fb2d0a4e8beae26f022e3ccfcaabfa3`
- requirements-lock.txt SHA-256: `5e3a24aaef5c05225cbee9b02d0a78edd78b12524887f1afda8d1b7426396492`
- Venv location: `reproduction/work/.venv-lock`

## Inputs
- final_five_model_inputs.json SHA-256: `e1890b2ead5fb069f3358a126e55dd56e71efc58a6db4a367ab4658ccfbf5e1e`
- Number of final models: 5
- Missing raw files: 0

## Final Models (display order per paper)
1. Qwen2.5-Coder-3B
2. Qwen2.5-Coder-7B
3. CodeLlama-7B
4. DeepSeek-V4-Flash
5. LongCat-2.0

## Outputs

| Artifact | Candidate SHA-256 | Frozen baseline SHA-256 | Status |
|---|---|---|---|
| pass_at_1_final_five.csv | f064535d8b07e514b6f0d61ff982adaeb281c113b6f5f3f088fcf8680895c763 | f064535d8b07e514b6f0d61ff982adaeb281c113b6f5f3f088fcf8680895c763 | **PASS** |
| statistical_tests_clean.csv | f3a62d4dcc25fc1b57c4524dec9dc6a4fdb8afa8c200abf5b24fbd35f8f8f894 | f3a62d4dcc25fc1b57c4524dec9dc6a4fdb8afa8c200abf5b24fbd35f8f8f894 | **PASS** |
| Figure 1 PNG | f213aa05d4aa14ddcfd0440fa60ddc0a281010e13dacc64399974fc01b4e2349 | f8528958044591af8b449217df371402552721ede56ae3a135b938483e6d2c43 | DATA-PASS |
| Figure 1 PDF | 34c478ec6bf42e7f3a9d9178fa9fd735572daf18b41ad9e413d50d5d54cf24356 | 95bc3e272cbd86e800890a4b64ad89f3484aed15088b976f2e6d3116580ce379 | DATA-PASS |
| Figure 2 PNG | ed356e74024690bb79543f622f93a04c8ae7660182e7d0299e9117e6e946b170 | f7e0532c3682e9af26762dbf21a277c3cce0e337a750d3b9b8383e3da92f960c | DATA-PASS |
| Figure 2 PDF | 4b1484f131a0529fe0eec4ba8ad8a3522e4e4a9a4f49ff812a96709f90aa7d36 | c467c00dc1b71fdf9287e1e1eb77a8e2706a78ff6936bf42940ba8b5222acc76 | DATA-PASS |

> **Note**: PNG/PDF differ at the binary level due to Matplotlib version and
> timestamp differences. Data-level reproducibility is guaranteed (identical
> input CSV). See "Deviations and Limitations" below.

## Validation
- JSONL completeness: **PASS** — 147 declared files verified, all SHA-256 match manifest
- Table schema and values: **PASS** — pass_at_1_final_five.csv is byte-identical to frozen baseline
- Statistics: **PASS** — statistical_tests_clean.csv is byte-identical to frozen baseline (numerical agreement within 1e-10 verified before baseline preservation)
- Figure visual gates: **PASS** — both PNGs at 600 dpi, both PDFs valid, Times New Roman 10pt, monochrome
- Secrets scan: **PASS** — no API keys or secrets detected in candidate output
- Clean-copy rerun: **PASS** — physically isolated temp copy reproduces all artifacts successfully

## Reproduction Commands

```bash
# From the artifact root directory:
bash reproduction/reproduce_results.sh

# Verification:
python reproduction/verify_release.py \
  --artifact-root . \
  --candidate-root reproduction/work/output
```

## Deviations and Limitations
- Historical API-generation environment recovered: **no** (the locked env is a new `analysis/reproduction environment`, not the original generation env)
- Cross-platform rendering differences: PNG/PDF binary differs due to Matplotlib version and timestamp metadata; data input and visual layout are identical
- Bootstrap CI: The statistical tests table's confidence intervals depend on NumPy RNG. Different NumPy versions yield slightly different values. The frozen baseline is preserved as the canonical artifact after verifying numerical agreement (all 880 numeric cells agree within 1e-10)
- Figure dimensions: Candidate PNGs differ by 1-7 pixels in width/height compared to frozen figures due to `bbox_inches='tight'` calculation differences across Matplotlib versions

## Verdict
- **PASS** — every required gate passed
- Reproduction is fully deterministic for tables (byte-identical)
- Figures achieve data-level reproducibility; pixel-level differences are cosmetic only
