def solve(packet: str) -> bool:
    if not validate_fluxon_packet(packet):
        return False
    record = parse_fluxon_packet(packet)
    return record["version"] >= 2 and record["channel"] == "gamma"
