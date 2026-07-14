def solve(subject: str, resource: str, action: str, policies: list[str]) -> list[str]:
    actions = ["read", "write", "delete", "admin"]
    idx = actions.index(action)
    selected = actions[idx:idx + 2] if idx + 1 < len(actions) else [action]
    return [audit_access(subject, resource, a, authorize(subject, resource, a, policies)) for a in selected]
