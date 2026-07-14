def solve(series_list: list[str]) -> int:
    if not series_list:
        return 0
    recs = [parse_nimbla_series(s) for s in series_list]
    all_ts = [t for rec in recs for t in rec['timestamps']]
    if not all_ts:
        return 0
    lo, hi = min(all_ts), max(all_ts)
    mid = (lo + hi) // 2
    selected = [select_nimbla_range(rec, lo, mid) for rec in recs]
    selected = [s for s in selected if s['values']]
    if not selected:
        return 0
    merged = selected[0]
    for rec in selected[1:]:
        merged = merge_nimbla_series(merged, rec)
    return len(merged['values'])
