def solve(series_list: list[str]) -> float:
    if not series_list:
        return 0.0
    stds = [summarize_nimbla(parse_nimbla_series(s))['std'] for s in series_list]
    return sum(stds) / len(stds)
