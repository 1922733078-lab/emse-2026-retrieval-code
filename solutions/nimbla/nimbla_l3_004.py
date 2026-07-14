def solve(series_list: list[str]) -> int:
    selected = []
    for s in series_list:
        rec = parse_nimbla_series(s)
        selected.append(select_nimbla_range(rec, 2, 10))
    selected = [s for s in selected if s['values']]
    if not selected:
        return 0
    merged = selected[0]
    for rec in selected[1:]:
        merged = merge_nimbla_series(merged, rec)
    return summarize_nimbla(merged)['count']
