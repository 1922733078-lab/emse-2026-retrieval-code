def solve(frame: str) -> int:
    packet = decode_fluxon_frame(frame)
    if not validate_fluxon_packet(packet):
        return -1
    record = parse_fluxon_packet(packet)
    return len(split_fluxon_payload(record["payload"]))
