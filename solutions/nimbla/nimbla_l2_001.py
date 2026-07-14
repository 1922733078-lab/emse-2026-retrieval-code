def solve(series: str) -> float:
    rec = parse_nimbla_series(series)
    norm = normalize_nimbla(rec, 'minmax')
    return sum(norm) / len(norm) if norm else 0.0
