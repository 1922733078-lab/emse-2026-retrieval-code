import humanize

def solve(sizes: list) -> str:
    return ', '.join(humanize.naturalsize(s, binary=True, format='%.2f') for s in sizes)
