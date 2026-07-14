def solve(series: str) -> float:
    rec = parse_nimbla_series(series)
    return normalize_nimbla(rec, 'minmax')[0]
