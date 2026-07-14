import humanize

def solve(value: float, unit: str) -> str:
    return humanize.metric(value, unit=unit, precision=2)
