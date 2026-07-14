def solve(history: list[dict]) -> str:
    if not history:
        return "intern"
    counts = {}
    for entry in history:
        action = entry.get("action", "read")
        counts[action] = counts.get(action, 0) + 1
    top_action = max(counts, key=counts.get)
    role = suggest_role(history)
    return role if action_priority(top_action) >= 2 else "intern"
