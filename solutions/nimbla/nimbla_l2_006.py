def solve(series: str, threshold: float) -> bool:
    rec = parse_nimbla_series(series)
    return summarize_nimbla(rec)['mean'] > threshold
