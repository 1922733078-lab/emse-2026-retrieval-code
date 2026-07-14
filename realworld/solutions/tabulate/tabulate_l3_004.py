import tabulate

def solve(rows: list, threshold: int) -> str:
    filtered = [r for r in rows if r[1] >= threshold]
    return tabulate.tabulate(filtered, headers=['Name', 'Score'], tablefmt='plain')
