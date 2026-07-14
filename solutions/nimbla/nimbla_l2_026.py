def solve(series: str, factor: float) -> float:
    rec = parse_nimbla_series(series)
    return summarize_nimbla(rec)['std'] * factor
