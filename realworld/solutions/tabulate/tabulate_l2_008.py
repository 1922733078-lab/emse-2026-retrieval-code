import tabulate

def solve(data: list) -> str:
    return tabulate.tabulate(data, headers=['I', 'F'], numalign='right', floatfmt='.3f', tablefmt='plain')
