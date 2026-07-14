def solve(series_list: list[str]) -> float:
    if not series_list:
        return 0.0
    avgs = []
    for s in series_list:
        rec = parse_nimbla_series(s)
        ma = moving_average(rec, 2)
        avgs.append(sum(ma) / len(ma) if ma else 0.0)
    return sum(avgs) / len(avgs)
