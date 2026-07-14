def solve(series: str) -> float:
    rec = parse_nimbla_series(series)
    return sum(normalize_nimbla(rec, 'zscore'))
