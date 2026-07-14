def solve(series_list: list[str], threshold: float) -> float:
    if not series_list:
        return 0.0
    recs = [parse_nimbla_series(s) for s in series_list]
    merged = recs[0]
    for rec in recs[1:]:
        merged = merge_nimbla_series(merged, rec)
    out_ts = set(detect_outliers(merged, threshold))
    vals = [v for t, v in zip(merged['timestamps'], merged['values']) if t in out_ts]
    return sum(vals) / len(vals) if vals else 0.0
