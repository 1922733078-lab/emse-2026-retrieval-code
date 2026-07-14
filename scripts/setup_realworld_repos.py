"""Clone and inspect candidate real-world repositories for E9."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REALWORLD_DIR = ROOT / "realworld"
REPOS = [
    {
        "name": "python-dateutil",
        "url": "https://github.com/dateutil/dateutil.git",
        "ref": "2.9.0.post0",
        "license": "BSD-3-Clause",
    },
    {
        "name": "humanize",
        "url": "https://github.com/python-humanize/humanize.git",
        "ref": "4.9.0",
        "license": "MIT",
    },
    {
        "name": "tabulate",
        "url": "https://github.com/astanin/python-tabulate.git",
        "ref": "v0.9.0",
        "license": "MIT",
    },
]


def clone_or_update(repo: dict[str, str]) -> tuple[Path, str]:
    dest = REALWORLD_DIR / "repos" / repo["name"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not (dest / ".git").exists():
        subprocess.run(
            ["git", "clone", repo["url"], str(dest)],
            check=True,
            capture_output=True,
        )
    subprocess.run(
        ["git", "fetch", "--tags"],
        cwd=dest,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", repo["ref"]],
        cwd=dest,
        check=True,
        capture_output=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=dest,
        check=True,
        capture_output=True,
        text=True,
    )
    commit = result.stdout.strip()
    return dest, commit


def main() -> None:
    REALWORLD_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"repos": []}
    for repo in REPOS:
        print(f"Setting up {repo['name']}...")
        dest, commit = clone_or_update(repo)
        manifest["repos"].append({
            "name": repo["name"],
            "path": str(dest.relative_to(ROOT)),
            "url": repo["url"],
            "ref": repo["ref"],
            "commit": commit,
            "license": repo["license"],
        })

    manifest_path = REALWORLD_DIR / "repo_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"Wrote repo manifest to {manifest_path}")


if __name__ == "__main__":
    main()
