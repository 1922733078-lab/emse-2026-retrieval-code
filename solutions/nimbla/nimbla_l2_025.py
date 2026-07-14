def solve(series: str) -> bool:
    rec = parse_nimbla_series(series)
    return forecast_next(rec, 'diff') > last_value(rec)
