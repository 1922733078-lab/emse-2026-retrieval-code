def solve(series_list: list[str]) -> float:
    values = []
    for s in series_list:
        rec = parse_nimbla_series(s)
        values.extend(rec['values'])
    return max(values) - min(values) if values else 0.0
