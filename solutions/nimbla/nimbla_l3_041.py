def solve(series_list: list[str], factor: float) -> list[float]:
    if not series_list:
        return []
    recs = [parse_nimbla_series(s) for s in series_list]
    merged = recs[0]
    for rec in recs[1:]:
        merged = merge_nimbla_series(merged, rec)
    scaled = scale_nimbla(merged, factor)
    return normalize_nimbla({'timestamps': merged['timestamps'], 'values': scaled}, 'minmax')
