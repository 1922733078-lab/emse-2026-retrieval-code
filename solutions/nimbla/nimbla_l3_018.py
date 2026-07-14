def solve(series_list: list[str]) -> str:
    entries = []
    for s in series_list:
        rec = parse_nimbla_series(s)
        if not rec['timestamps']:
            continue
        nxt = forecast_next(rec, 'diff')
        ts = rec['timestamps'][-1] + 1
        entries.append(format_nimbla_series([ts], [nxt]))
    if not entries:
        return 'NIM|'
    body = ','.join(e.split('|', 1)[1] for e in entries)
    return 'NIM|' + body
