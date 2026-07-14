import tabulate

def solve(rows: list) -> str:
    return tabulate.tabulate(rows, headers=['Item', 'Value'], floatfmt='.1f', tablefmt='grid')
