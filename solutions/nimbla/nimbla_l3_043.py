def solve(series_list: list[str]) -> float:
    diffs = []
    for s in series_list:
        rec = parse_nimbla_series(s)
        diffs.extend(value_differences(rec))
    return sum(diffs) / len(diffs) if diffs else 0.0
