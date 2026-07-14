import tabulate

def solve(rows: list) -> str:
    total = sum(v for _, v in rows)
    normalized = [[name, round(v / total * 100, 1)] for name, v in rows]
    return tabulate.tabulate(normalized, headers=['Name', 'Pct'], floatfmt='.1f', tablefmt='plain')
