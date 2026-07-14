def solve(series: str, factor: float) -> float:
    rec = parse_nimbla_series(series)
    return sum(scale_nimbla(rec, factor))
