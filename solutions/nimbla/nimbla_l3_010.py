def solve(series_list: list[str], threshold: float) -> list[int]:
    return [len(detect_outliers(parse_nimbla_series(s), threshold)) for s in series_list]
