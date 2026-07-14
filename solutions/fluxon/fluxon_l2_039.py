def solve(packet: str) -> float:
    record = parse_fluxon_packet(packet)
    values = [token_value(t) for t in split_fluxon_payload(record["payload"])]
    avg = sum(values) / len(values) if values else 0.0
    return normalize_channel_value(avg, record["channel"])
