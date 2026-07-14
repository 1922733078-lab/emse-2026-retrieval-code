import humanize

def solve(side_m: float) -> str:
    return humanize.metric(side_m ** 2, unit='m²', precision=2)
