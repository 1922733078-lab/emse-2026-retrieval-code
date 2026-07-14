import humanize

def solve(sizes: list) -> str:
    return '|'.join(humanize.naturalsize(s, gnu=True) for s in sizes)
