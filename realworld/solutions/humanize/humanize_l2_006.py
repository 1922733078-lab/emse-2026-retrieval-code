import humanize

def solve(value: float) -> str:
    return humanize.clamp(value, format='{:.0f}', floor=0, ceil=100, floor_token='≤', ceil_token='≥')
