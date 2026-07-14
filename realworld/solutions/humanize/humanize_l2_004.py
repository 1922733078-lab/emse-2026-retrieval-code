import humanize

def solve(n: int, gender: str) -> str:
    return humanize.ordinal(n, gender=gender)
