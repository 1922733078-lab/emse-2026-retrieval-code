def solve(packet: str) -> float:
    record = parse_fluxon_packet(packet)
    checksum = compute_fluxon_checksum(record["payload"], record["version"])
    return normalize_channel_value(checksum, record["channel"])
