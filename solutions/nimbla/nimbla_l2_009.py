def solve(series: str) -> float:
    rec = parse_nimbla_series(series)
    diffs = value_differences(rec)
    return sum(diffs) / len(diffs) if diffs else 0.0
