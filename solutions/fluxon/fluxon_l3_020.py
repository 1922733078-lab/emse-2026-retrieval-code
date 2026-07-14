def solve(packets: list[str]) -> dict:
    valid = [parse_fluxon_packet(p) for p in packets if validate_fluxon_packet(p)]
    return summarize_fluxon_records(valid)
