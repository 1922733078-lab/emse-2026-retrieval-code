def solve(series: str) -> list[float]:
    rec = parse_nimbla_series(series)
    return normalize_nimbla(rec, 'zscore')
