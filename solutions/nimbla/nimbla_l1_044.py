def solve(series: str) -> float:
    rec = parse_nimbla_series(series)
    return summarize_nimbla(rec)['min']
