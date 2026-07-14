def solve(packets: list[str]) -> int:
    count = 0
    for packet in packets:
        if not validate_fluxon_packet(packet):
            continue
        record = parse_fluxon_packet(packet)
        if record["channel"] == "gamma" and not is_legacy_packet(record):
            count += 1
    return count
