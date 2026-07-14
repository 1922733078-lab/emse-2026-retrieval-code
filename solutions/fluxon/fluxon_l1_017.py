def solve(packet: str) -> str:
    return parse_fluxon_packet(packet)["channel"]
