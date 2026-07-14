def solve(series_list: list[str], threshold: float) -> dict[int, list[int]]:
    return {i: detect_outliers(parse_nimbla_series(s), threshold) for i, s in enumerate(series_list)}
