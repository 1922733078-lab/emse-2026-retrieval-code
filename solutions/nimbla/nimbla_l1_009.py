def solve(series: str, index: int) -> int:
    return parse_nimbla_series(series)['timestamps'][index]
