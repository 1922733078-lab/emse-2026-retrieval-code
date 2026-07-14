def solve(subject: str, resources: list[str], action: str, policies: list[str]) -> int:
    return sum(1 for resource in resources if authorize(subject, resource, action, policies))
