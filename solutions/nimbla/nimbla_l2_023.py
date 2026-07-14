def solve(series: str, threshold: float) -> str:
    rec = parse_nimbla_series(series)
    out_ts = detect_outliers(rec, threshold)
    out_set = set(out_ts)
    ts = [t for t in rec['timestamps'] if t in out_set]
    vals = [v for t, v in zip(rec['timestamps'], rec['values']) if t in out_set]
    return format_nimbla_series(ts, vals)
