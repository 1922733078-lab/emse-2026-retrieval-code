def solve(packets: list[str]) -> str | None:
    best = None
    best_score = -1
    for packet in packets:
        if not validate_fluxon_packet(packet):
            continue
        record = parse_fluxon_packet(packet)
        if record["channel"] not in {"alpha", "beta"}:
            continue
        score = sum(token_value(t) for t in split_fluxon_payload(record["payload"]))
        if score > best_score:
            best_score = score
            best = packet
    return best
