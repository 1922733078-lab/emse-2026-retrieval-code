import tabulate

def solve(data: list) -> str:
    return tabulate.tabulate(data, headers=['Name', 'Score'], tablefmt='pipe')
