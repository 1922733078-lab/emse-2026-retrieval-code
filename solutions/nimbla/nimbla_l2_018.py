def solve(series: str) -> int:
    rec = parse_nimbla_series(series)
    s = format_nimbla_series(rec['timestamps'], rec['values'])
    return series_length(parse_nimbla_series(s))
