import humanize

def solve(lo: float, hi: float) -> str:
    return f"{humanize.clamp(lo, format='{:.0f}', floor=0)}-{humanize.clamp(hi, format='{:.0f}', ceil=100)}"
