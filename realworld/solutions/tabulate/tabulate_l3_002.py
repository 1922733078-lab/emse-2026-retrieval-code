import tabulate

def solve(rows: list) -> str:
    return tabulate.tabulate(rows, headers=['A', 'B'], showindex=True, missingval='?', tablefmt='plain')
