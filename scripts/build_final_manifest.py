"""Build final_five_model_inputs.json manifest for the five-model study.

Explicitly lists each model and experiment family, excluding GPT-5.5 and
MiniMax-M2.5.  The manifest is intended for stage G result freezing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_DIR = ROOT / "outputs" / "manifests"
MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

MODELS = {
    "qwen_3b": "Qwen2.5-Coder-3B-Instruct",
    "qwen_7b": "Qwen2.5-Coder-7B-Instruct",
    "codellama": "CodeLlama-7B-Instruct-Q5_K_M",
    "deepseek_v4_flash": "DeepSeek-V4-Flash",
    "longcat_2_0": "LongCat-2.0",
}

EXPERIMENTS = {
    "E1_main": {
        "qwen_3b": "qwen_3b.jsonl",
        "qwen_7b": "qwen_7b.jsonl",
        "codellama": "codellama_7b_instruct_q5_k_m.jsonl",
        "deepseek_v4_flash": "deepseek_v4_flash_main.jsonl",
        "longcat_2_0": "longcat_2_0_main.jsonl",
    },
    "E2_topk": {
        "qwen_3b": "qwen3b_naive_topk_full.jsonl",
        "qwen_7b": "qwen7b_naive_topk_full.jsonl",
        "codellama": "codellama_naive_topk_full.jsonl",
        "deepseek_v4_flash": "deepseek_v4_flash_naive_topk_full.jsonl",
        "longcat_2_0": "longcat_2_0_naive_topk_full.jsonl",
    },
    "E3a_gold_reminder": {
        "qwen_3b": "qwen3b_gold_reminder_full.jsonl",
        "qwen_7b": "qwen7b_gold_reminder_full.jsonl",
        "codellama": "codellama_gold_reminder_full.jsonl",
        "deepseek_v4_flash": "deepseek_v4_flash_gold_reminder_full.jsonl",
        "longcat_2_0": "longcat_2_0_gold_reminder_full.jsonl",
    },
    "E3b_distractor_reminder": {
        "qwen_3b": "qwen3b_distractor_reminder_full.jsonl",
        "qwen_7b": "qwen7b_distractor_reminder_full.jsonl",
        "codellama": "codellama_distractor_reminder_full.jsonl",
        "deepseek_v4_flash": "deepseek_v4_flash_distractor_reminder_full.jsonl",
        "longcat_2_0": "longcat_2_0_distractor_reminder_full.jsonl",
    },
    "E4_pass3": {
        "qwen_3b": "p1_qwen3b_n3.jsonl",
        "qwen_7b": "p1_qwen7b_n3.jsonl",
        "codellama": "p1_codellama_n3.jsonl",
        "deepseek_v4_flash": "p1_deepseek_v4_flash_n3.jsonl",
        "longcat_2_0": "p1_longcat_2_0_n3.jsonl",
    },
    "E5_cot": {
        "qwen_3b": "p0_qwen3b_cot.jsonl",
        "qwen_7b": "p0_qwen7b_cot.jsonl",
        "codellama": "p0_codellama_cot.jsonl",
        "deepseek_v4_flash": "p0_deepseek_v4_flash_cot.jsonl",
        "longcat_2_0": "p0_longcat_2_0_cot.jsonl",
    },
    "E7_retriever_robustness": {
        "qwen_3b": "e7_qwen3b.jsonl",
        "qwen_7b": "e7_qwen7b.jsonl",
        "codellama": "e7_codellama.jsonl",
        "deepseek_v4_flash": "e7_deepseek-v4-flash_dense.jsonl",
        "deepseek_v4_flash_hybrid": "e7_deepseek-v4-flash_hybrid.jsonl",
        "longcat_2_0": "e7_LongCat-2.0_dense.jsonl",
        "longcat_2_0_hybrid": "e7_LongCat-2.0_hybrid.jsonl",
    },
    "E8_distractor_intensity": {
        "qwen_3b": "e8_qwen3b.jsonl",
        "qwen_7b": "e8_qwen7b.jsonl",
        "codellama": "e8_codellama.jsonl",
        "deepseek_v4_flash_weak": "e8_deepseek-v4-flash_distractor_weak.jsonl",
        "deepseek_v4_flash_strong": "e8_deepseek-v4-flash_distractor_strong.jsonl",
        "longcat_2_0_weak": "e8_LongCat-2.0_distractor_weak.jsonl",
        "longcat_2_0_strong": "e8_LongCat-2.0_distractor_strong.jsonl",
    },
    "E9_realworld": {
        "qwen_3b": "realworld/outputs/raw_generations/e9_qwen3b.jsonl",
        "qwen_7b": "realworld/outputs/raw_generations/e9_qwen7b.jsonl",
        "codellama": "realworld/outputs/raw_generations/e9_codellama.jsonl",
        "deepseek_v4_flash": "realworld/outputs/raw_generations/e9_deepseek_v4_flash_async.jsonl",
        "longcat_2_0": "realworld/outputs/raw_generations/e9_longcat_2_0_async.jsonl",
    },
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def derive_paths(raw_name: str) -> dict[str, str | None]:
    if raw_name.startswith("../") or raw_name.startswith("realworld/"):
        raw = ROOT / raw_name
    else:
        raw = ROOT / "outputs" / "raw_generations" / raw_name
    tested = raw.parent.parent / "test_results" / f"{raw.stem}_results.jsonl"
    metrics = raw.parent.parent / "metrics" / f"{raw.stem}_metrics.jsonl"
    return {
        "raw": str(raw.relative_to(ROOT)),
        "raw_exists": raw.exists(),
        "raw_sha256": sha256_file(raw) if raw.exists() else None,
        "tested": str(tested.relative_to(ROOT)) if tested.is_relative_to(ROOT) else str(tested),
        "tested_exists": tested.exists(),
        "tested_sha256": sha256_file(tested) if tested.exists() else None,
        "metrics": str(metrics.relative_to(ROOT)) if metrics.is_relative_to(ROOT) else str(metrics),
        "metrics_exists": metrics.exists(),
        "metrics_sha256": sha256_file(metrics) if metrics.exists() else None,
    }


def main() -> None:
    manifest: dict[str, Any] = {
        "models": MODELS,
        "experiments": {},
    }
    for exp_name, files in EXPERIMENTS.items():
        manifest["experiments"][exp_name] = {}
        for model_alias, raw_name in files.items():
            manifest["experiments"][exp_name][model_alias] = derive_paths(raw_name)

    missing = [
        f"{exp}/{model}"
        for exp, models in manifest["experiments"].items()
        for model, info in models.items()
        if not info["raw_exists"]
    ]
    manifest["missing_raw_files"] = missing

    out_path = MANIFEST_DIR / "final_five_model_inputs.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"Wrote manifest to {out_path}")
    print(f"Missing raw files: {len(missing)}")
    for m in missing:
        print(f"  - {m}")


if __name__ == "__main__":
    main()
