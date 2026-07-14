def solve(subject: str, policies: list[str]) -> dict[str, bool]:
    sensitivities = ["low", "medium", "high", "critical"]
    return {s: authorize(subject, format_resource("doc", s, "eng"), "read", policies) for s in sensitivities}
