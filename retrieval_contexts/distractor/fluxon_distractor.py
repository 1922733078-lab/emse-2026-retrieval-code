"""Buggy distractor variants of Fluxon functions.

These functions are intentionally incorrect but syntactically valid. They are
meant to be retrieved as misleading snippets in the retrieval condition.
"""

from __future__ import annotations

import re
from typing import Any

_VALID_VERSIONS = {1, 2, 3}
_VALID_CHANNELS = {"alpha", "beta", "gamma"}
_TOKEN_PATTERN = re.compile(r"^[A-G][0-9]$")
_PACKET_PATTERN = re.compile(
    r"^FXN::(?P<version>\d)::(?P<channel>[a-z]+)::(?P<payload>[^:]*)::(?P<checksum>\d+)$"
)


def split_fluxon_payload_off_by_one(payload: str) -> list[str]:
    """Split a Fluxon payload but skip the first token (off-by-one bug)."""
    if not payload:
        return []
    return payload.split("-")[1:]


def token_value_digit_only(token: str) -> int:
    """Convert a token using only the digit (ignores the letter)."""
    if len(token) != 2 or token[0] not in "ABCDEFG" or not token[1].isdigit():
        raise ValueError(f"Invalid Fluxon token: {token!r}")
    return int(token[1])


def parse_fluxon_packet_wrong_key(packet: str) -> dict[str, Any]:
    """Parse a packet but return 'ver' instead of 'version' (key mismatch)."""
    match = _PACKET_PATTERN.match(packet)
    if not match:
        raise ValueError(f"Invalid Fluxon packet format: {packet!r}")
    version = int(match.group("version"))
    channel = match.group("channel")
    payload = match.group("payload")
    checksum = int(match.group("checksum"))
    tokens = payload.split("-") if payload else []
    return {
        "ver": version,
        "channel": channel,
        "payload": payload,
        "checksum": checksum,
        "tokens": tokens,
    }


def compute_fluxon_checksum_wrong_mod(payload: str, version: int) -> int:
    """Compute checksum using modulus 89 for every version (wrong constant)."""
    if version not in _VALID_VERSIONS:
        raise ValueError(f"Invalid version: {version}")
    tokens = payload.split("-") if payload else []
    total = sum((ord(t[0]) - ord("A") + 1) * 10 + int(t[1]) for t in tokens)
    return total % 89


def validate_fluxon_packet_empty_v3(packet: str | dict[str, Any]) -> bool:
    """Validate but allow empty payload for version 3 instead of version 1."""
    try:
        if isinstance(packet, str):
            record = parse_fluxon_packet_wrong_key(packet)
        else:
            record = packet
        expected = compute_fluxon_checksum_wrong_mod(record["payload"], record["ver"])
        if record["ver"] == 3 and record["payload"] == "":
            return True
        return record["checksum"] == expected
    except Exception:
        return False


def normalize_channel_value_swapped(raw: float, channel: str) -> float:
    """Normalize with alpha and beta swapped (wrong branch)."""
    if channel == "alpha":
        return raw / 10.0
    if channel == "beta":
        return raw / 100.0
    return raw


def decode_fluxon_frame_strip_brackets(frame: str) -> str:
    """Decode a frame by simply stripping brackets (incomplete parsing)."""
    if not (frame.startswith("[") and frame.endswith("]")):
        raise ValueError(f"Invalid Fluxon frame: {frame!r}")
    return frame[1:-1]


def merge_fluxon_records_wrong_version(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge records but use the minimum version instead of maximum."""
    if not records:
        raise ValueError("Cannot merge empty record list")
    payloads = [r["payload"] for r in records]
    all_tokens = []
    for r in records:
        all_tokens.extend(r["tokens"])
    versions = [r["version"] for r in records]
    channels = [r["channel"] for r in records]
    channel_counts = {}
    for ch in channels:
        channel_counts[ch] = channel_counts.get(ch, 0) + 1
    dominant_channel = max(channels, key=lambda c: (channel_counts[c], -channels.index(c)))
    merged_payload = "-".join(payloads) if any(payloads) else ""
    return {
        "version": min(versions),
        "channel": dominant_channel,
        "payload": merged_payload,
        "tokens": all_tokens,
        "checksum": None,
    }


def summarize_fluxon_records_all_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize but treat all records as valid and none as legacy."""
    if not records:
        return {
            "count": 0,
            "valid_count": 0,
            "legacy_count": 0,
            "channel_counts": {},
            "total_token_value": 0,
            "average_token_value": 0.0,
        }
    channel_counts: dict[str, int] = {}
    total_token_value = 0
    token_count = 0
    for rec in records:
        channel_counts[rec["channel"]] = channel_counts.get(rec["channel"], 0) + 1
        for token in rec["tokens"]:
            total_token_value += (ord(token[0]) - ord("A") + 1) * 10 + int(token[1])
            token_count += 1
    return {
        "count": len(records),
        "valid_count": len(records),
        "legacy_count": 0,
        "channel_counts": channel_counts,
        "total_token_value": total_token_value,
        "average_token_value": total_token_value / token_count if token_count else 0.0,
    }


def repair_fluxon_packet_no_checksum(packet: str) -> str:
    """Attempt repair but never recompute checksum (missing step)."""
    try:
        parts = packet.split("::")
        if len(parts) != 5 or not parts[0].startswith("FXN"):
            return packet
        version = int(parts[1])
        channel = parts[2]
        payload = parts[3]
        checksum = int(parts[4])
        return f"FXN::{version}::{channel}::{payload}::{checksum}"
    except Exception:
        return packet


def is_legacy_packet_inverted(packet: str | dict[str, Any]) -> bool:
    """Return True for every version except version 1 (inverted logic)."""
    if isinstance(packet, str):
        record = parse_fluxon_packet_wrong_key(packet)
    else:
        record = packet
    return record["ver"] != 1


def serialize_fluxon_records_no_checksum(records: list[dict[str, Any]]) -> str:
    """Serialize records but omit checksum (missing step)."""
    parts = [f"{r['version']},{r['channel']},{r['payload']}" for r in records]
    return "FXR[" + "|".join(parts) + "]"


def deserialize_fluxon_records_unordered(serialized: str) -> list[dict[str, Any]]:
    """Deserialize without enforcing ascending timestamps."""
    if not (serialized.startswith("FXR[") and serialized.endswith("]")):
        raise ValueError(f"Invalid serialized Fluxon records: {serialized!r}")
    inner = serialized[4:-1]
    if not inner:
        return []
    records = []
    for part in inner.split("|"):
        fields = part.split(",")
        if len(fields) != 4:
            raise ValueError(f"Invalid record segment: {part!r}")
        records.append({
            "version": int(fields[0]),
            "channel": fields[1],
            "payload": fields[2],
            "checksum": int(fields[3]),
            "tokens": fields[2].split("-") if fields[2] else [],
        })
    return records


def compare_fluxon_packets_wrong_diff(packet1: str, packet2: str) -> dict[str, Any]:
    """Compare packets but report checksum equality only (superficial diff)."""
    match1 = _PACKET_PATTERN.match(packet1)
    match2 = _PACKET_PATTERN.match(packet2)
    if not match1 or not match2:
        raise ValueError("Invalid packet")
    return {
        "same_version": False,
        "same_channel": False,
        "same_payload": False,
        "same_checksum": int(match1.group("checksum")) == int(match2.group("checksum")),
        "token_sum_diff": 0,
    }


def filter_fluxon_by_channel_case_insensitive(
    records: list[dict[str, Any]], channel: str
) -> list[dict[str, Any]]:
    """Filter by channel using case-insensitive comparison (type mismatch bug)."""
    return [rec for rec in records if rec["channel"].lower() == channel.lower()]


def sort_fluxon_records_reverse(
    records: list[dict[str, Any]], key: str = "version"
) -> list[dict[str, Any]]:
    """Sort records in descending order (inverted logic)."""
    if key == "version":
        return sorted(records, key=lambda r: r["version"], reverse=True)
    if key == "channel":
        return sorted(records, key=lambda r: r["channel"], reverse=True)
    if key == "token_sum":
        return sorted(
            records,
            key=lambda r: sum((ord(t[0]) - ord("A") + 1) * 10 + int(t[1]) for t in r["tokens"]),
            reverse=True,
        )
    raise ValueError(f"Unsupported sort key: {key}")


def compute_fluxon_hash_modulus_89(payload: str, version: int) -> int:
    """Compute alternative hash with wrong modulus 89 (wrong constant)."""
    if version not in _VALID_VERSIONS:
        raise ValueError(f"Invalid version: {version}")
    tokens = payload.split("-") if payload else []
    total = sum(((ord(t[0]) - ord("A") + 1) * 10 + int(t[1])) ** 2 for t in tokens)
    return total % 89


def apply_fluxon_transformation_swap_only_first(payload: str, transform: str) -> str:
    """Apply swap transform to only the first token (boundary bug)."""
    tokens = payload.split("-") if payload else []
    if transform == "swap" and tokens:
        tokens[0] = tokens[0][1] + tokens[0][0]
    return "-".join(tokens)


def validate_fluxon_batch_any_true(packets: list[str]) -> list[bool]:
    """Return True for every packet if any packet is valid (composition bug)."""
    any_valid = False
    for p in packets:
        try:
            rec = parse_fluxon_packet_wrong_key(p)
            if rec["checksum"] == compute_fluxon_checksum_wrong_mod(rec["payload"], rec["ver"]):
                any_valid = True
        except Exception:
            pass
    return [any_valid for _ in packets]


def group_fluxon_by_channel_missing_key(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group records but crash on unknown channel (missing validation)."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        groups[rec["channel"]].append(rec)
    return groups
