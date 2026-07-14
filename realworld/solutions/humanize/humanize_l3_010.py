import humanize

def solve(values: list) -> str:
    return ', '.join(humanize.fractional(v) for v in values)
