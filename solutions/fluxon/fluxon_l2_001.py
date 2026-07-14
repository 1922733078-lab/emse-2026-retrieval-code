def solve(packet: str) -> bool:
    record = parse_fluxon_packet(packet)
    if record["version"] == 1 and record["channel"] == "beta":
        tokens = split_fluxon_payload(record["payload"])
        if len(tokens) == 2:
            return True
    return validate_fluxon_packet(packet)
