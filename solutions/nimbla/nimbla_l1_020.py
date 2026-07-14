def solve(series: str, window: int) -> list[float]:
    rec = parse_nimbla_series(series)
    return moving_average(rec, window)
