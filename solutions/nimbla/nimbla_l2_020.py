def solve(series: str, factor: float, threshold: float) -> list[int]:
    rec = parse_nimbla_series(series)
    scaled = scale_nimbla(rec, factor)
    return detect_outliers({'timestamps': rec['timestamps'], 'values': scaled}, threshold)
