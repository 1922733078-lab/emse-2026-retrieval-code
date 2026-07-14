import humanize

def solve(items: list) -> str:
    return '\n'.join(f"{k}: {humanize.intword(v)}" for k, v in items)
