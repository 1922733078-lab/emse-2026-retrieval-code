import tabulate

def solve(rows: list, fmt: str) -> str:
    return tabulate.tabulate(rows, headers=['A', 'B'], tablefmt=fmt)
