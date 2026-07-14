def solve(series_list: list[str]) -> int:
    if not series_list:
        return 0
    recs = [parse_nimbla_series(s) for s in series_list]
    merged = recs[0]
    for rec in recs[1:]:
        merged = merge_nimbla_series(merged, rec)
    return sum(1 for d in value_differences(merged) if d > 0)
