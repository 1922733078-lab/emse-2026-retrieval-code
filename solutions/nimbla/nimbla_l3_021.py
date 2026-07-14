def solve(series_list: list[str]) -> int:
    total = 0
    for s in series_list:
        rec = parse_nimbla_series(s)
        total += series_length(rec)
    return total
