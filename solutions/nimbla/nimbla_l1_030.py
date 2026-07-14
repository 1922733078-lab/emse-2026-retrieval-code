def solve(series: str) -> float:
    rec = parse_nimbla_series(series)
    return max(normalize_nimbla(rec, 'minmax'))
