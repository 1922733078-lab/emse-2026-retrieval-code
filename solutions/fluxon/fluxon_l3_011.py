def solve(packets: list[str]) -> int:
    valid = [parse_fluxon_packet(p) for p in packets if validate_fluxon_packet(p)]
    if not valid:
        return 0
    merged = merge_fluxon_records(valid)
    return compute_fluxon_checksum(merged["payload"], merged["version"])
