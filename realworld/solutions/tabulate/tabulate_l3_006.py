import tabulate

def solve(dicts: list) -> str:
    return tabulate.tabulate(dicts, headers='keys', tablefmt='grid')
