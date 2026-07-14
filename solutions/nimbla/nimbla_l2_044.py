def solve(series: str, window: int) -> float:
    rec = parse_nimbla_series(series)
    return max(moving_average(rec, window))
