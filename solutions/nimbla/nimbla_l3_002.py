def solve(series_list: list[str], threshold: float) -> int:
    total = 0
    for s in series_list:
        rec = parse_nimbla_series(s)
        total += len(detect_outliers(rec, threshold))
    return total
