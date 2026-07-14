def solve(series1: str, series2: str) -> int:
    rec1 = parse_nimbla_series(series1)
    rec2 = parse_nimbla_series(series2)
    merged = merge_nimbla_series(rec1, rec2)
    return len(rec1['timestamps']) + len(rec2['timestamps']) - len(merged['timestamps'])
