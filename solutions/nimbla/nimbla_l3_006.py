def solve(series_list: list[str], threshold: float) -> list[int]:
    outs = set()
    for s in series_list:
        rec = parse_nimbla_series(s)
        outs.update(detect_outliers(rec, threshold))
    return sorted(outs)
