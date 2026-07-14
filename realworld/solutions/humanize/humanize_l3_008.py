import humanize

def solve(x: float) -> str:
    if abs(x) >= 1:
        return humanize.metric(x, unit='g', precision=2)
    return humanize.scientific(x, precision=2)
