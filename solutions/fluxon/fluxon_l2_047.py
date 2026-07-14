def solve(packet: str, new_channel: str) -> str:
    record = parse_fluxon_packet(packet)
    return format_fluxon_packet(record["version"], new_channel, record["payload"])
