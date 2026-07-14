def solve(series_list: list[str]) -> float:
    all_norm = []
    for s in series_list:
        rec = parse_nimbla_series(s)
        if len(rec['values']) >= 4:
            all_norm.extend(normalize_nimbla(rec, 'minmax'))
    return sum(all_norm) / len(all_norm) if all_norm else 0.0
