def solve(frames: list[str]) -> dict[str, float]:
    groups = {}
    for frame in frames:
        packet = decode_fluxon_frame(frame)
        if not validate_fluxon_packet(packet):
            continue
        record = parse_fluxon_packet(packet)
        total = sum(token_value(t) for t in split_fluxon_payload(record["payload"]))
        norm = normalize_channel_value(total, record["channel"])
        groups.setdefault(record["channel"], []).append(norm)
    return {ch: sum(vals) / len(vals) for ch, vals in groups.items()}
