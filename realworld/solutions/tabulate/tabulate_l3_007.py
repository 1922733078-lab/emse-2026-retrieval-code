import tabulate

def solve(rows: list) -> str:
    return tabulate.tabulate(rows, headers=['A', 'B'], tablefmt=tabulate.simple_separated_format('::'))
