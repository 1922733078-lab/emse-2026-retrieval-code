import humanize

def solve(x: float) -> str:
    return humanize.clamp(x, floor=0, ceil=10)
