def solve(series_list: list[str]) -> float:
    recs = [parse_nimbla_series(s) for s in series_list]
    if not recs:
        return 0.0
    merged = recs[0]
    for rec in recs[1:]:
        merged = merge_nimbla_series(merged, rec)
    norm = normalize_nimbla(merged, 'minmax')
    return sum(norm) / len(norm) if norm else 0.0
