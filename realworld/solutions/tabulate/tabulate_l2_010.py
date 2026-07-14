import tabulate

def solve(data: list) -> str:
    return tabulate.tabulate(data, headers=['VeryLongHeader'], maxheadercolwidths=[4], tablefmt='plain')
