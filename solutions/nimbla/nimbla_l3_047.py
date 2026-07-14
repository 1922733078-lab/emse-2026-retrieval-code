def solve(series_list: list[str], threshold: float) -> list[int]:
    if not series_list:
        return []
    recs = [parse_nimbla_series(s) for s in series_list]
    merged = recs[0]
    for rec in recs[1:]:
        merged = merge_nimbla_series(merged, rec)
    ma = moving_average(merged, 2)
    return detect_outliers({'timestamps': merged['timestamps'], 'values': ma}, threshold)
