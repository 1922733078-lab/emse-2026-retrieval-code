def solve(series: str, factor: float, window: int) -> list[float]:
    rec = parse_nimbla_series(series)
    scaled = scale_nimbla(rec, factor)
    return moving_average({'timestamps': rec['timestamps'], 'values': scaled}, window)
