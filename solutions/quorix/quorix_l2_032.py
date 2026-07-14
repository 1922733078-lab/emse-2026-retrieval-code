def solve(subject: str, resource: str, policies: list[str]) -> str | None:
    allowed = list_allowed_actions(subject, resource, policies)
    return max(allowed, key=action_priority) if allowed else None
