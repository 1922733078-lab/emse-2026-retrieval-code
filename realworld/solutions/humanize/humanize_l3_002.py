import humanize

def solve(n: int) -> str:
    return f"{humanize.intcomma(n)} ({humanize.intword(n)})"
