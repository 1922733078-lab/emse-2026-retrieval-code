import tabulate

def solve(data: list) -> str:
    return tabulate.tabulate(data, disable_numparse=True, tablefmt='plain')
