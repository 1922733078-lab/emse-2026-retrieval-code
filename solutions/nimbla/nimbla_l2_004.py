def solve(series: str) -> str:
    rec = parse_nimbla_series(series)
    nxt = forecast_next(rec, 'last')
    ts = rec['timestamps'][-1] + 1 if rec['timestamps'] else 1
    return format_nimbla_series([ts], [nxt])
