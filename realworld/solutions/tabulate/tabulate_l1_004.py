import tabulate

def solve(data: list) -> str:
    return tabulate.tabulate(data, headers=['Name', 'Score'], tablefmt=tabulate.simple_separated_format('|'))
