import humanize

def solve(n: int) -> str:
    return f"{humanize.apnumber(n)} {humanize.ordinal(n)}"
