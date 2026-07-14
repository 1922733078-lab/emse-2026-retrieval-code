def solve(packets: list[str]) -> int:
    return sum(1 for p in packets if validate_fluxon_packet(repair_fluxon_packet(p)))
