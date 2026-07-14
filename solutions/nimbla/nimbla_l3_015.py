def solve(series_list: list[str], factor: float, threshold: float) -> list[int]:
    if not series_list:
        return []
    scaled = []
    for s in series_list:
        rec = parse_nimbla_series(s)
        scaled.append({'timestamps': rec['timestamps'], 'values': scale_nimbla(rec, factor)})
    merged = scaled[0]
    for rec in scaled[1:]:
        merged = merge_nimbla_series(merged, rec)
    return detect_outliers(merged, threshold)
