def solve(series: str, threshold: float) -> bool:
    rec = parse_nimbla_series(series)
    return len(detect_outliers(rec, threshold)) > 0
