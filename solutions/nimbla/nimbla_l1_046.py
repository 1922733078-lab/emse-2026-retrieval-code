def solve(series: str) -> float:
    rec = parse_nimbla_series(series)
    s = summarize_nimbla(rec)
    return s['max'] - s['min']
