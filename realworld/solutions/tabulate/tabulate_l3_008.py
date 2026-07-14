import tabulate

def solve(rows: list) -> str:
    return tabulate.tabulate(rows, headers=['Name', 'Score'], tablefmt='pipe')
