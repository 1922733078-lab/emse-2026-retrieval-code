def solve(packets: list[str]) -> dict[str, float]:
    channel_totals = {}
    for packet in packets:
        if not validate_fluxon_packet(packet):
            continue
        record = parse_fluxon_packet(packet)
        total = sum(token_value(t) for t in split_fluxon_payload(record["payload"]))
        norm = normalize_channel_value(total, record["channel"])
        channel_totals.setdefault(record["channel"], []).append(norm)
    return {ch: max(vals) for ch, vals in channel_totals.items()}
