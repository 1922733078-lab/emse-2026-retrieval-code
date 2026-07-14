def solve(histories: list[list[dict]]) -> str:
    if not histories:
        return "intern"
    suggestions = [suggest_role(h) for h in histories]
    counts = {role: suggestions.count(role) for role in suggestions}
    max_count = max(counts.values())
    for role in suggestions:
        if counts[role] == max_count:
            return role
    return suggestions[0]
