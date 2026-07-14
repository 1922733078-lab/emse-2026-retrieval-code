import tabulate

def solve(data: list) -> str:
    return tabulate.tabulate(data, headers=['X', 'Y'], colalign=('left', 'right'), tablefmt='plain')
