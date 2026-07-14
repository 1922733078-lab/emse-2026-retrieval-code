def solve(subject: str, resource: str, action: str, policies: list[str]) -> bool:
    return authorize(subject, resource, action, policies, default=True)
