def solve(packet: str) -> float:
    if not validate_fluxon_packet(packet):
        return -1.0
    record = parse_fluxon_packet(packet)
    total = sum(token_value(t) for t in split_fluxon_payload(record["payload"]))
    return normalize_channel_value(total, record["channel"])
