def solve(history: list[dict]) -> str:
    role = suggest_role(history)
    return make_policy(f'role == "{role}"', "allow")
