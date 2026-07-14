import humanize

def solve(n: float) -> str:
    return humanize.naturalsize(n, binary=True)
