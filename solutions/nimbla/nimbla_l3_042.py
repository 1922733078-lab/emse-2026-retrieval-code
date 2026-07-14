def solve(series_list: list[str]) -> str:
    ts = []
    vals = []
    for s in series_list:
        rec = parse_nimbla_series(s)
        if rec['timestamps']:
            ts.append(rec['timestamps'][-1] + 1)
            vals.append(forecast_next(rec, 'last'))
    return format_nimbla_series(ts, vals)
