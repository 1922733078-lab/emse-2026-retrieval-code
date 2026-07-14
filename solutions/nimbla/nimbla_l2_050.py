def solve(series: str) -> int:
    rec = parse_nimbla_series(series)
    return sum(1 for d in value_differences(rec) if d < 0)
