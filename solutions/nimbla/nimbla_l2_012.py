def solve(series: str, threshold: float) -> float:
    rec = parse_nimbla_series(series)
    out_ts = set(detect_outliers(rec, threshold))
    return sum(v for t, v in zip(rec['timestamps'], rec['values']) if t in out_ts)
