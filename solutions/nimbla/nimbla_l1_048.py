def solve(series: str, start: int, end: int) -> list[float]:
    rec = parse_nimbla_series(series)
    return select_nimbla_range(rec, start, end)['values']
