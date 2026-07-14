def solve(series: str) -> float:
    rec = parse_nimbla_series(series)
    return forecast_next(rec, 'mean') - last_value(rec)
