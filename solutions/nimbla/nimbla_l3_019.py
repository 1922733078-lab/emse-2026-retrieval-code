def solve(series_list: list[str], threshold: float) -> str:
    ts = []
    vals = []
    for s in series_list:
        rec = parse_nimbla_series(s)
        out_ts = set(detect_outliers(rec, threshold))
        for t, v in zip(rec['timestamps'], rec['values']):
            if t in out_ts:
                ts.append(t)
                vals.append(v)
    return format_nimbla_series(ts, vals)
