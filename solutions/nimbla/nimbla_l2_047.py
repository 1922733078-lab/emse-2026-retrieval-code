def solve(series: str, factor: float) -> str:
    rec = parse_nimbla_series(series)
    scaled = scale_nimbla(rec, factor)
    return format_nimbla_series(rec['timestamps'], scaled)
