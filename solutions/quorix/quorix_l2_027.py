def solve(subject: str, resource: str, action: str, policies: list[str]) -> bool:
    return count_matching_policies(subject, resource, action, policies) >= 1
