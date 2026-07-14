def solve(series: str, window: int) -> float:
    rec = parse_nimbla_series(series)
    ma = moving_average(rec, window)
    return ma[window - 1]
