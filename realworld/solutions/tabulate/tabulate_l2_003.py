import tabulate

def solve(data: list) -> str:
    return tabulate.tabulate(data, headers=['A', 'B'], tablefmt=tabulate.simple_separated_format(','), floatfmt='.2f')
