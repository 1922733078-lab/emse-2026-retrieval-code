def solve(series_list: list[str]) -> dict:
    if not series_list:
        return summarize_nimbla({'timestamps': [], 'values': []})
    recs = [parse_nimbla_series(s) for s in series_list]
    merged = recs[0]
    for rec in recs[1:]:
        merged = merge_nimbla_series(merged, rec)
    return summarize_nimbla(merged)
