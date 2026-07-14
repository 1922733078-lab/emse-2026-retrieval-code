def solve(series_list: list[str]) -> float:
    selected = [select_nimbla_range(parse_nimbla_series(s), 1, 20) for s in series_list]
    selected = [s for s in selected if s['values']]
    if not selected:
        return 0.0
    merged = selected[0]
    for rec in selected[1:]:
        merged = merge_nimbla_series(merged, rec)
    return forecast_next(merged, 'mean')
