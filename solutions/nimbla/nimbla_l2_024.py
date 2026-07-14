def solve(series: str) -> float:
    rec = parse_nimbla_series(series)
    w = series_length(rec)
    ma = moving_average(rec, w)
    return sum(ma) / len(ma) if ma else 0.0
