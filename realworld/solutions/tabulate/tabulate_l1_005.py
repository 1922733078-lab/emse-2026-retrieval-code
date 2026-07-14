import tabulate

def solve(data: list) -> str:
    return tabulate.tabulate(data, floatfmt='.2f', tablefmt='plain')
