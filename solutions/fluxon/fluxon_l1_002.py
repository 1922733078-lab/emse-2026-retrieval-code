def solve(packet: str) -> int:
    record = parse_fluxon_packet(packet)
    return compute_fluxon_checksum(record["payload"], record["version"])
