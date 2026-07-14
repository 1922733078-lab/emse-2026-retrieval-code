def solve(series: str, start: int, end: int) -> int:
    rec = parse_nimbla_series(series)
    sub = select_nimbla_range(rec, start, end)
    return summarize_nimbla(sub)['count']
