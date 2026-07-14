import tabulate

def solve(data: list) -> str:
    return tabulate.tabulate(data, showindex=True, tablefmt='plain')
