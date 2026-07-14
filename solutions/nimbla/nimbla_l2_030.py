def solve(series: str) -> bool:
    rec = parse_nimbla_series(series)
    norm = normalize_nimbla(rec, 'minmax')
    return all(0.0 <= v <= 1.0 for v in norm)
