def solve(series_list: list[str]) -> list[float]:
    result = []
    for s in series_list:
        rec = parse_nimbla_series(s)
        result.extend(moving_average(rec, 2))
    return result
