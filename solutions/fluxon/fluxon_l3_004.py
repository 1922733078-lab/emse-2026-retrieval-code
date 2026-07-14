def solve(frames: list[str]) -> float:
    values = []
    for frame in frames:
        packet = decode_fluxon_frame(frame)
        if validate_fluxon_packet(packet):
            record = parse_fluxon_packet(packet)
            total = sum(token_value(t) for t in split_fluxon_payload(record["payload"]))
            values.append(normalize_channel_value(total, record["channel"]))
    return sum(values) / len(values) if values else 0.0
