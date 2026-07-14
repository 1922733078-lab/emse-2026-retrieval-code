def solve(series_list: list[str]) -> float:
    means = []
    for s in series_list:
        rec = parse_nimbla_series(s)
        if len(rec['values']) >= 3:
            means.append(summarize_nimbla(rec)['mean'])
    return sum(means) / len(means) if means else 0.0
