def solve(policies: list[str]) -> str:
    ordered = resolve_policies(policies)
    return ordered[0]["effect"] if ordered else ""
