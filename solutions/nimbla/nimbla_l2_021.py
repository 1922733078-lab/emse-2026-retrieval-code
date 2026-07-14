def solve(series: str) -> float:
    rec = parse_nimbla_series(series)
    norm = normalize_nimbla(rec, 'zscore')
    return max(abs(v) for v in norm) if norm else 0.0
