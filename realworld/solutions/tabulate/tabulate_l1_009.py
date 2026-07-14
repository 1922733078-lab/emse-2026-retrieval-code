import tabulate

def solve(data: list) -> str:
    return tabulate.tabulate(data, headers=['Name'], stralign='center', tablefmt='plain')
