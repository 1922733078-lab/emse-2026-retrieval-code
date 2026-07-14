def solve(policies: list[str]) -> bool:
    allows = set()
    denies = set()
    for policy in policies:
        p = parse_policy(policy)
        # Extract a role literal from a simple condition like 'role == "manager"'.
        import re
        m = re.search(r'role\s*==\s*"([^"]+)"', p["condition"])
        if m:
            role = m.group(1)
            if p["effect"] == "allow":
                allows.add(role)
            else:
                denies.add(role)
    return bool(allows & denies)
