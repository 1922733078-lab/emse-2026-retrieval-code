def solve(packet1: str, packet2: str) -> int:
    rec1 = parse_fluxon_packet(packet1)
    rec2 = parse_fluxon_packet(packet2)
    merged = merge_fluxon_records([rec1, rec2])
    return compute_fluxon_checksum(merged["payload"], merged["version"])
