def solve(series: str) -> str:
    rec = parse_nimbla_series(series)
    nxt = forecast_next(rec, 'mean')
    ts = rec['timestamps'] + [rec['timestamps'][-1] + 1]
    vals = rec['values'] + [nxt]
    return format_nimbla_series(ts, vals)
