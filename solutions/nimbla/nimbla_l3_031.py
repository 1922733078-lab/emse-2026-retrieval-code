def solve(series_list: list[str]) -> int:
    count = 0
    for s in series_list:
        try:
            parse_nimbla_series(s)
            count += 1
        except ValueError:
            pass
    return count
