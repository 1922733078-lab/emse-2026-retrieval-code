def solve(series: str, factor: float) -> list[float]:
    rec = parse_nimbla_series(series)
    scaled = scale_nimbla(rec, factor)
    return normalize_nimbla({'timestamps': rec['timestamps'], 'values': scaled}, 'minmax')
