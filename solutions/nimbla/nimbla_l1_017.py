def solve(series: str) -> int:
    rec = parse_nimbla_series(series)
    return series_length(parse_nimbla_series(format_nimbla_series(rec['timestamps'], rec['values'])))
