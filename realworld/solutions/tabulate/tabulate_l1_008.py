import tabulate

def solve(data: list) -> str:
    return tabulate.tabulate(data, headers=['A', 'B'], numalign='right', tablefmt='plain')
