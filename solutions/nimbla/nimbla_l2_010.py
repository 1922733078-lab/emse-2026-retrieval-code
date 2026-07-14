def solve(series: str) -> int:
    rec = parse_nimbla_series(series)
    empty = {'timestamps': [], 'values': []}
    return series_length(merge_nimbla_series(rec, empty))
