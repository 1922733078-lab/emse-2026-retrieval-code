def solve(series: str, start: int, end: int) -> list[float]:
    rec = parse_nimbla_series(series)
    sub = select_nimbla_range(rec, start, end)
    return normalize_nimbla(sub, 'minmax')
