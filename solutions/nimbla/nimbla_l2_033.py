def solve(series: str) -> float:
    rec = parse_nimbla_series(series)
    s = summarize_nimbla(rec)
    return s['std'] / s['mean'] if s['mean'] != 0 else 0.0
