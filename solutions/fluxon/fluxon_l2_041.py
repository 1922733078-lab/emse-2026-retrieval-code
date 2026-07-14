def solve(packet: str) -> bool:
    if not validate_fluxon_packet(packet):
        return False
    record = parse_fluxon_packet(packet)
    tokens = split_fluxon_payload(record["payload"])
    return len(tokens) != len(set(tokens))
