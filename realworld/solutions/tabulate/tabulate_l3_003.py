import tabulate

def solve(data: list) -> str:
    transposed = list(zip(*data))
    return tabulate.tabulate(transposed, headers='firstrow', tablefmt='plain')
