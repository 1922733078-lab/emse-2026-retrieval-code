"""Build distractor_weak and distractor_strong contexts for E8 robustness.

Transformations are deterministic and pre-registered.  We start from the
existing distractor snippets and apply two mutation strategies:

* weak: obvious errors (glaring constants, broken names, contradictory docs)
* strong: subtle boundary/constant/branch mutations that preserve plausibility
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "retrieval_contexts" / "distractor"
OUT_DIR = ROOT / "retrieval_contexts"
RANDOM_SEED = 20260710


def weaken(snippet: str) -> str:
    """Make distractor errors obvious."""
    s = snippet
    # Rename internal-looking wrong helpers to obviously broken names.
    s = re.sub(r"\b(\w+_wrong_\w+)\b", r"\1_obviously_broken", s)
    # Replace common wrong constants with absurd values.
    s = re.sub(r"% 89", "% 99999", s)
    s = re.sub(r"% 97", "% 88888", s)
    s = re.sub(r"% 101", "% 77777", s)
    # Add a glaring comment in the docstring.
    s = re.sub(
        r'(""".*?)(\.)?(""")',
        r'\1. NOTE: this implementation is intentionally wrong and should not be used.\3',
        s,
        flags=re.DOTALL,
    )
    return s


def strengthen(snippet: str) -> str:
    """Make distractor errors subtle but still semantically wrong."""
    s = snippet
    # Slightly tweak wrong modulus values.
    s = re.sub(r"% 89", "% 87", s)
    s = re.sub(r"% 97", "% 95", s)
    s = re.sub(r"% 101", "% 99", s)
    # Swap a few boundary/branch constants.
    s = re.sub(r"== 3", "== 2", s)
    s = re.sub(r"== 1", "== 0", s)
    s = re.sub(r"version not in", "version in", s)
    # Flip boolean defaults.
    s = re.sub(r"return True\n(\s+)return False", r"return False\n\1return True", s)
    return s


def transform_context(src_path: Path, transform) -> dict[str, list[str]]:
    with src_path.open(encoding="utf-8") as f:
        ctx = json.load(f)
    out = {}
    for task_id, snippets in ctx.items():
        out[task_id] = [transform(s) for s in snippets]
    return out


def main() -> None:
    weak_dir = OUT_DIR / "distractor_weak"
    strong_dir = OUT_DIR / "distractor_strong"
    weak_dir.mkdir(parents=True, exist_ok=True)
    strong_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "source": "retrieval_contexts/distractor",
        "random_seed": RANDOM_SEED,
        "transformations": {
            "weak": [
                "rename wrong_* helpers to *_obviously_broken",
                "replace modulus constants with absurd values (89->99999, etc.)",
                "append 'intentionally wrong' note to docstrings",
            ],
            "strong": [
                "slightly change modulus constants (89->87, etc.)",
                "swap version boundary checks (==3 -> ==2, ==1 -> ==0)",
                "invert membership checks (not in -> in)",
                "flip trailing True/False return pairs",
            ],
        },
    }

    for lib in ("fluxon", "quorix", "nimbla"):
        src = SRC_DIR / f"{lib}.json"
        if not src.exists():
            print(f"Missing {src}, skipping")
            continue
        weak_ctx = transform_context(src, weaken)
        strong_ctx = transform_context(src, strengthen)

        with (weak_dir / f"{lib}.json").open("w", encoding="utf-8") as f:
            json.dump(weak_ctx, f, ensure_ascii=False, indent=2)
        with (strong_dir / f"{lib}.json").open("w", encoding="utf-8") as f:
            json.dump(strong_ctx, f, ensure_ascii=False, indent=2)
        print(f"Wrote {lib} weak ({len(weak_ctx)}) and strong ({len(strong_ctx)})")

    manifest_path = OUT_DIR / "distractor_intensity_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"Wrote manifest to {manifest_path}")


if __name__ == "__main__":
    main()
