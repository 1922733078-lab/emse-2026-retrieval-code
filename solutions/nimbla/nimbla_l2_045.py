def solve(series: str, threshold: float) -> float:
    rec = parse_nimbla_series(series)
    out_ts = set(detect_outliers(rec, threshold))
    vals = [v for t, v in zip(rec['timestamps'], rec['values']) if t in out_ts]
    return min(vals) if vals else -1.0
