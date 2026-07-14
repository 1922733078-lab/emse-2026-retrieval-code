import humanize

def solve(n: float) -> str:
    return humanize.naturalsize(n, binary=True, format='%.2f')
