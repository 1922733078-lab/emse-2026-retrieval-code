import tabulate

def solve(data: list) -> str:
    return tabulate.tabulate(data, missingval='N/A', tablefmt='plain')
