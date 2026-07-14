def solve(subject: str, resources: list[str], action: str, policies: list[str]) -> list[str]:
    return [resource for resource in resources if authorize(subject, resource, action, policies)]
