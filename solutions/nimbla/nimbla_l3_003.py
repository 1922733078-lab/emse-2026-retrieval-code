def solve(series_list: list[str]) -> str:
    if not series_list:
        return 'NIM|'
    recs = [parse_nimbla_series(s) for s in series_list]
    merged = recs[0]
    for rec in recs[1:]:
        merged = merge_nimbla_series(merged, rec)
    nxt = forecast_next(merged, 'last')
    ts = merged['timestamps'][-1] + 1 if merged['timestamps'] else 1
    return format_nimbla_series([ts], [nxt])
