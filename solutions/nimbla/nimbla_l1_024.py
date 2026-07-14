def solve(series: str, threshold: float) -> list[int]:
    rec = parse_nimbla_series(series)
    return detect_outliers(rec, threshold)
