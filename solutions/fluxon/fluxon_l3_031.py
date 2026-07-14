def solve(frames: list[str]) -> list[int]:
    result = []
    for frame in frames:
        packet = decode_fluxon_frame(frame)
        if validate_fluxon_packet(packet):
            record = parse_fluxon_packet(packet)
            if record["version"] >= 2:
                result.append(record["checksum"])
    return result
