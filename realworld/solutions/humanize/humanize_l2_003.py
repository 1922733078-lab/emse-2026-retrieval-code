import humanize

def solve(n) -> str:
    return humanize.intword(n, format='%.2f')
