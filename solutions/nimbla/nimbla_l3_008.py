def solve(series_list: list[str]) -> float:
    if not series_list:
        return 0.0
    recs = [parse_nimbla_series(s) for s in series_list]
    merged = recs[0]
    for rec in recs[1:]:
        merged = merge_nimbla_series(merged, rec)
    ma = moving_average(merged, 2)
    return ma[-1] if ma else 0.0
