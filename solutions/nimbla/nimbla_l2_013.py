def solve(series: str, window: int, threshold: float) -> list[int]:
    rec = parse_nimbla_series(series)
    ma = moving_average(rec, window)
    return detect_outliers({'timestamps': rec['timestamps'], 'values': ma}, threshold)
