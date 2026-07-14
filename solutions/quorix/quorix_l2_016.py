def solve(subject: str, resource: str, action: str, policies: list[str]) -> str:
    decision = authorize(subject, resource, action, policies)
    return audit_access(subject, resource, action, decision)
