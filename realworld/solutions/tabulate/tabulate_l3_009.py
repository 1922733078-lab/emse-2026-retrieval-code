import tabulate

def solve(rows: list) -> str:
    return tabulate.tabulate(rows, headers=['X', 'Y'], colalign=('left', 'right'), floatfmt='.2f', tablefmt='plain')
