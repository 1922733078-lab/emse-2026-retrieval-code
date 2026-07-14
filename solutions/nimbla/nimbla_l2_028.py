def solve(series: str, start: int, end: int) -> float:
    rec = parse_nimbla_series(series)
    sub = select_nimbla_range(rec, start, end)
    if not sub['values']:
        return 0.0
    return forecast_next(sub, 'last')
