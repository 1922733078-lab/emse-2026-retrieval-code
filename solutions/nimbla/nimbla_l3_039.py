def solve(series_list: list[str], threshold: float) -> list[int]:
    if not series_list:
        return []
    selected = [select_nimbla_range(parse_nimbla_series(s), 2, 20) for s in series_list]
    selected = [s for s in selected if s['values']]
    if not selected:
        return []
    merged = selected[0]
    for rec in selected[1:]:
        merged = merge_nimbla_series(merged, rec)
    return detect_outliers(merged, threshold)
