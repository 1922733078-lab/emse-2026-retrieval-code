def solve(series: str) -> int:
    rec = parse_nimbla_series(series)
    return series_length(merge_nimbla_series(rec, rec))
