def solve(series_list: list[str]) -> float:
    if not series_list:
        return 0.0
    recs = [parse_nimbla_series(s) for s in series_list]
    merged = recs[0]
    for rec in recs[1:]:
        merged = merge_nimbla_series(merged, rec)
    if not merged['timestamps']:
        return 0.0
    mid_idx = len(merged['timestamps']) // 2
    mid_ts = merged['timestamps'][mid_idx]
    selected = select_nimbla_range(merged, merged['timestamps'][0], mid_ts)
    return forecast_next(selected, 'last') if selected['values'] else 0.0
