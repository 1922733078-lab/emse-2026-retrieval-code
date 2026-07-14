def solve(series: str, threshold: float) -> int:
    rec = parse_nimbla_series(series)
    outs = detect_outliers(rec, threshold)
    return outs[0] if outs else -1
