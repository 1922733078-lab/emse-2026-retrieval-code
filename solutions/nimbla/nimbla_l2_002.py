def solve(series: str) -> int:
    rec = parse_nimbla_series(series)
    norm = normalize_nimbla(rec, 'zscore')
    return sum(1 for v in norm if v > 0)
