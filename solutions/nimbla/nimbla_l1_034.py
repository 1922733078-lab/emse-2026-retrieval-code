def solve(series1: str, series2: str) -> list[float]:
    rec1 = parse_nimbla_series(series1)
    rec2 = parse_nimbla_series(series2)
    return merge_nimbla_series(rec1, rec2)['values']
