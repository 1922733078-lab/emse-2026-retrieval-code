def solve(series: str) -> int:
    rec = parse_nimbla_series(series)
    mean = summarize_nimbla(rec)['mean']
    return sum(1 for v in rec['values'] if v > mean)
