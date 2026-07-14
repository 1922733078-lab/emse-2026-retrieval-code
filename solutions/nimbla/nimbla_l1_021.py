def solve(series: str) -> list[float]:
    rec = parse_nimbla_series(series)
    return moving_average(rec, 2)
