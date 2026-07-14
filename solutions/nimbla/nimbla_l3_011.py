def solve(series_list: list[str], threshold: float) -> int:
    if not series_list:
        return 0
    recs = [parse_nimbla_series(s) for s in series_list]
    merged = recs[0]
    for rec in recs[1:]:
        merged = merge_nimbla_series(merged, rec)
    return len(detect_outliers(merged, threshold))
