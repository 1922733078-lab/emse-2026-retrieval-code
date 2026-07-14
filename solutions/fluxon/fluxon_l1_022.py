def solve(packet: str) -> int:
    record = parse_fluxon_packet(packet)
    return len(split_fluxon_payload(record["payload"]))
