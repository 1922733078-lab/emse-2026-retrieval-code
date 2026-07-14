def solve(series_list: list[str], threshold: float) -> int:
    outs = []
    for s in series_list:
        rec = parse_nimbla_series(s)
        outs.extend(detect_outliers(rec, threshold))
    return min(outs) if outs else -1
