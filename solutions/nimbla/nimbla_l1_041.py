def solve(series: str) -> int:
    rec = parse_nimbla_series(series)
    return summarize_nimbla(rec)['count']
