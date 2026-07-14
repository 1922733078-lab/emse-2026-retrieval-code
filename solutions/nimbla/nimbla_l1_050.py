def solve(series: str) -> int:
    rec = parse_nimbla_series(series)
    return len(value_differences(rec))
