def solve(packet: str) -> int:
    return parse_fluxon_packet(packet)["version"]
