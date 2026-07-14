def solve(subject: str, resource: str, policies: list[str]) -> list[str]:
    return list_allowed_actions(subject, resource, policies)
