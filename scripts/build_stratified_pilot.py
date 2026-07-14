"""Build a stratified 90-task pilot sample for LongCat calibration.

Fixes seed 20260710. For each library x difficulty (L1/L2/L3), sample 10 tasks.
Outputs tasks/longcat_pilot_90.jsonl and a manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from collections import defaultdict


def library_from_task_id(task_id: str) -> str:
    return task_id.split("_")[0]


def build_pilot(tasks_path: Path, seed: int, out_path: Path, manifest_path: Path) -> None:
    with tasks_path.open(encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f]

    rng = random.Random(seed)

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for task in tasks:
        lib = library_from_task_id(task["task_id"])
        level = task["level"]
        groups[(lib, level)].append(task)

    selected: list[dict] = []
    for (lib, level), group in sorted(groups.items()):
        if len(group) < 10:
            raise ValueError(f"Not enough tasks for {lib}/{level}: {len(group)}")
        sampled = rng.sample(group, 10)
        sampled.sort(key=lambda t: t["task_id"])
        selected.extend(sampled)

    # Preserve original order of all_tasks.jsonl within selected.
    selected_ids = {t["task_id"] for t in selected}
    selected_in_original_order = [t for t in tasks if t["task_id"] in selected_ids]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for task in selected_in_original_order:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")

    sha256 = hashlib.sha256(out_path.read_bytes()).hexdigest()
    manifest = {
        "tasks_path": str(tasks_path),
        "out_path": str(out_path),
        "seed": seed,
        "n_tasks": len(selected_in_original_order),
        "selected_task_ids": [t["task_id"] for t in selected_in_original_order],
        "counts_per_lib_level": {
            f"{lib}_{level}": 10 for (lib, level) in sorted(groups.keys())
        },
        "sha256": sha256,
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(selected_in_original_order)} tasks to {out_path}")
    print(f"Manifest: {manifest_path}")
    print(f"SHA-256: {sha256}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, default=Path("tasks/all_tasks.jsonl"))
    parser.add_argument("--seed", type=int, default=20260710)
    parser.add_argument("--output", type=Path, default=Path("tasks/longcat_pilot_90.jsonl"))
    parser.add_argument("--manifest", type=Path, default=Path("outputs/manifests/longcat_pilot_90_manifest.json"))
    args = parser.parse_args()
    build_pilot(args.tasks, args.seed, args.output, args.manifest)


if __name__ == "__main__":
    main()
