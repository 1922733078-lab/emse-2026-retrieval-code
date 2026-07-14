def solve(series_list: list[str]) -> int:
    count = 0
    for s in series_list:
        rec = parse_nimbla_series(s)
        count += sum(1 for v in normalize_nimbla(rec, 'zscore') if v > 0)
    return count
