def solve(policies: list[str]) -> list[str]:
    return [p["effect"] for p in resolve_policies(policies)]
