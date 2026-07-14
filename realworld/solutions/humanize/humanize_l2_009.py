import humanize

def solve(value, ndigits: int) -> str:
    return humanize.intcomma(value, ndigits=ndigits)
