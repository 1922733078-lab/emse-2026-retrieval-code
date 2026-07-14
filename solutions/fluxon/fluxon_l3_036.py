def solve(packets: list[str]) -> bool:
    if not packets:
        return False
    has_legacy = False
    for packet in packets:
        if not validate_fluxon_packet(packet):
            return False
        if is_legacy_packet(packet):
            has_legacy = True
    return has_legacy
