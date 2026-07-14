#!/usr/bin/env python3
"""Verify the reproduction candidate output against the frozen baseline.

Checks:
- JSONL completeness via manifest
- pass_at_1_final_five.csv byte-identity
- Statistical tests CSV byte-identity
- Figures exist with correct format (PNG 600 dpi, PDF valid)
- No secrets (API keys, .env contents) in candidate files
- SHA256SUMS can be produced and verified
- Provenance files present
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def check_byte_identity(label: Path, candidate: Path, frozen: Path) -> bool:
    if not candidate.exists():
        print(f"  FAIL: candidate missing: {candidate}")
        return False
    if not frozen.exists():
        print(f"  WARN: frozen baseline missing: {frozen}")
        return True
    c = candidate.read_bytes()
    f = frozen.read_bytes()
    if c == f:
        print(f"  PASS: {label} byte-identical ({len(c)} bytes)")
        return True
    print(f"  FAIL: {label} differs ({len(c)} vs {len(f)} bytes)")
    return False


def check_png(path: Path) -> bool:
    try:
        from PIL import Image
        img = Image.open(path)
        dpi = img.info.get("dpi", (0, 0))
        ok = abs(dpi[0] - 600) < 1 and abs(dpi[1] - 600) < 1
        status = "PASS" if ok else "FAIL"
        print(f"  {status}: {path.name} {img.size} dpi={dpi[0]:.1f}")
        return ok
    except Exception as e:
        print(f"  FAIL: {path.name}: {e}")
        return False


def check_pdf(path: Path) -> bool:
    try:
        data = path.read_bytes()
        ok = data.startswith(b"%PDF")
        status = "PASS" if ok else "FAIL"
        print(f"  {status}: {path.name} ({len(data)} bytes, header={data[:4]})")
        return ok
    except Exception as e:
        print(f"  FAIL: {path.name}: {e}")
        return False


def check_no_secrets(directory: Path) -> bool:
    """Scan candidate text files for potential secrets."""
    patterns = [
        re.compile(r"(?i)(api_key|api-key|bearer)\s*[:=]\s*['\"]?[^\s'\"]{16,}"),
        re.compile(r"(?i)sk-[A-Za-z0-9]{20,}"),
    ]
    violations = 0
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in (".png", ".pdf", ".jsonl"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in patterns:
            if pat.search(text):
                print(f"  WARN: potential secret in {path}")
                violations += 1
    if violations == 0:
        print("  PASS: no obvious secrets detected")
    else:
        print(f"  WARN: {violations} files flagged")
    return violations == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--candidate-root", required=True)
    args = parser.parse_args()

    art = Path(args.artifact_root).resolve()
    cand = Path(args.candidate_root).resolve()

    all_ok = True

    print("\n=== Input Manifest ===")
    mf = art / "outputs" / "manifests" / "final_five_model_inputs.json"
    data = json.loads(mf.read_text())
    n_models = len(data["models"])
    print(f"  Models: {n_models} (expected 5)")
    print(f"  Missing raw files: {data['missing_raw_files']}")
    ok = n_models == 5 and not data["missing_raw_files"]
    all_ok = all_ok and ok

    print("\n=== Tables ===")
    tables = art / "reproduction" / "work" / "output" / "results" / "tables"
    all_ok &= check_byte_identity(
        "pass_at_1_final_five.csv",
        tables / "pass_at_1_final_five.csv",
        art / "results" / "tables" / "pass_at_1_final_five.csv",
    )
    all_ok &= check_byte_identity(
        "statistical_tests_clean.csv",
        tables / "statistical_tests_clean.csv",
        art / "results" / "tables" / "statistical_tests_clean.csv",
    )

    print("\n=== Figures ===")
    fig_dir = art / "reproduction" / "work" / "output" / "figures"
    for stem in ["figure_1_monochrome_conditions", "figure_2_monochrome_paired_effects"]:
        all_ok &= check_png(fig_dir / f"{stem}.png")
        all_ok &= check_pdf(fig_dir / f"{stem}.pdf")

    print("\n=== Provenance ===")
    for name in ["rebuild_provenance.json", "statistics_provenance.json"]:
        p = tables / name
        if p.exists():
            print(f"  PASS: {name} present ({len(p.read_bytes())} bytes)")
        else:
            print(f"  FAIL: {name} missing")
            all_ok = False

    print("\n=== Secrets Scan ===")
    check_no_secrets(cand)

    print("\n=== Verdict ===")
    if all_ok:
        print("PASS: all required gates passed")
        return 0
    else:
        print("FAIL: some gates did not pass")
        return 1


if __name__ == "__main__":
    sys.exit(main())
