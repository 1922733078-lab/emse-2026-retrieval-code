def solve(series_list: list[str]) -> float:
    if not series_list:
        return 0.0
    forecasts = [forecast_next(parse_nimbla_series(s), 'mean') for s in series_list]
    return sum(forecasts) / len(forecasts)
