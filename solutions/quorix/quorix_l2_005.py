def solve(subject: str, required_role: str, min_level: int) -> bool:
    return subject_has_role(subject, required_role) and subject_level_at_least(subject, min_level)
