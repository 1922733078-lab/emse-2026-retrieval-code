import tabulate

def solve(data: list) -> str:
    return tabulate.tabulate(data, intfmt='04d', tablefmt='plain')
