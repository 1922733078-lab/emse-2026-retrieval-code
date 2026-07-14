def solve(series: str) -> float:
    rec = parse_nimbla_series(series)
    diffs = value_differences(rec)
    avg = sum(diffs) / len(diffs) if diffs else 0.0
    return last_value(rec) + avg
