def solve(subject: str, resources: list[str], policies: list[str]) -> dict[str, list[str]]:
    return {resource: list_allowed_actions(subject, resource, policies) for resource in resources}
