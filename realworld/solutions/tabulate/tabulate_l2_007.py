import tabulate

def solve(data: list) -> str:
    return tabulate.tabulate(data, headers='keys', tablefmt='simple')
