def solve(series: str) -> float:
    rec = parse_nimbla_series(series)
    norm = normalize_nimbla(rec, 'minmax')
    return min(rec['values']) + max(rec['values'])
