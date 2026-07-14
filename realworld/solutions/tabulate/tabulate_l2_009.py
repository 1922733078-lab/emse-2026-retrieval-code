import tabulate

def solve(data: list) -> str:
    return tabulate.tabulate(data, headers=['X', 'Y'], showindex=['a', 'b'], tablefmt='plain')
