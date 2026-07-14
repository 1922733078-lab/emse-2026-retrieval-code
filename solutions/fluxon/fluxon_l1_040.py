def solve(packet: str) -> int:
    record = parse_fluxon_packet(packet)
    return sum(token_value(t) for t in split_fluxon_payload(record["payload"]))
