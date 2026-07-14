def solve(series: str) -> float:
    rec = parse_nimbla_series(series)
    return round(forecast_next(rec, 'mean'), 1)
