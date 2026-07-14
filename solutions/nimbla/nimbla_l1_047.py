def solve(series: str, start: int, end: int) -> int:
    rec = parse_nimbla_series(series)
    sub = select_nimbla_range(rec, start, end)
    return series_length(sub)
