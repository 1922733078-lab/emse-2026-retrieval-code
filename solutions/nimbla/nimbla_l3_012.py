def solve(series_list: list[str]) -> list[float]:
    result = []
    for s in series_list:
        rec = parse_nimbla_series(s)
        norm = normalize_nimbla(rec, 'minmax')
        result.append(max(norm) if norm else 0.0)
    return result
