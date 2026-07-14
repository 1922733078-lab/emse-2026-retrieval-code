def solve(subject: str, resource: str, action: str, policies: list[str]) -> bool:
    if not is_sensitive(resource, "medium"):
        return False
    return authorize(subject, resource, action, policies)
