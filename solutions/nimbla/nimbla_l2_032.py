def solve(series: str, threshold: float) -> float:
    rec = parse_nimbla_series(series)
    outs = detect_outliers(rec, threshold)
    return sum(outs) / len(outs) if outs else -1.0
