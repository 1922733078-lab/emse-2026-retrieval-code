def solve(series: str, start: int, end: int, window: int) -> list[float]:
    rec = parse_nimbla_series(series)
    sub = select_nimbla_range(rec, start, end)
    return moving_average(sub, window)
