import humanize

def solve(ratio: float) -> str:
    return humanize.clamp(ratio * 100, format='{:.1f}%', floor=0, ceil=100)
