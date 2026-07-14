def solve(series: str, threshold: float) -> int:
    rec = parse_nimbla_series(series)
    return len(detect_outliers(rec, threshold))
