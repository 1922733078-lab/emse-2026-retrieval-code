import tabulate

def solve(data: list) -> str:
    return tabulate.tabulate(data, headers=['Long'], maxcolwidths=[5], tablefmt='plain')
