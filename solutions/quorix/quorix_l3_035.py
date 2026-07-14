def solve(subject: str, resources: list[str], policies: list[str]) -> dict:
    allowed = sum(1 for r in resources if authorize(subject, r, "read", policies))
    return {"total": len(resources), "allowed": allowed, "denied": len(resources) - allowed}
