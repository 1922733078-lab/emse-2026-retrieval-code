def solve(subjects: list[str], resource: str, policies: list[str]) -> str | None:
    best = None
    best_count = -1
    for subject in subjects:
        count = len(list_allowed_actions(subject, resource, policies))
        if count > best_count:
            best_count = count
            best = subject
    return best if best_count > 0 else None
