def solve(series_list: list[str]) -> list[float]:
    if not series_list:
        return []
    recs = [parse_nimbla_series(s) for s in series_list]
    merged = recs[0]
    for rec in recs[1:]:
        merged = merge_nimbla_series(merged, rec)
    selected = select_nimbla_range(merged, 2, 15)
    return normalize_nimbla(selected, 'minmax')
