"""Fluxon Protocol Toolkit.

A synthetic Python library for parsing, validating, transforming, and repairing
Fluxon packets. The Fluxon protocol is entirely fictional and designed for
controlled experiments on retrieval-augmented code generation.

Packet format::

    FXN::<version>::<channel>::<payload>::<checksum>

Examples:

    FXN::2::alpha::A7-B3-C5::42
    FXN::1::beta::A2::15

Rules:
    * version must be 1, 2, or 3.
    * channel must be one of "alpha", "beta", "gamma".
    * payload is a dash-separated list of tokens (e.g. "A7-B3-C5").
    * each token is an uppercase letter A-G followed by a single digit 0-9.
    * checksum is computed from the token values and depends on the version.
"""

from __future__ import annotations

import math
import re
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_VERSIONS = {1, 2, 3}
_VALID_CHANNELS = {"alpha", "beta", "gamma"}
_TOKEN_PATTERN = re.compile(r"^[A-G][0-9]$")
_PACKET_PATTERN = re.compile(
    r"^FXN::(?P<version>\d)::(?P<channel>[a-z]+)::(?P<payload>[^:]*)::(?P<checksum>\d+)$"
)

_CHECKSUM_MODULUS = {1: 89, 2: 97, 3: 113}
_CHANNEL_NORMALIZER = {"alpha": 100.0, "beta": 10.0, "gamma": 1.0}


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def split_fluxon_payload(payload: str) -> list[str]:
    """Split a Fluxon payload into its tokens.

    Args:
        payload: A string like "A7-B3-C5". Empty payload yields an empty list.

    Returns:
        A list of token strings.
    """
    if not payload:
        return []
    return payload.split("-")


def token_value(token: str) -> int:
    """Convert a single Fluxon token to its numeric value.

    The letter A-G maps to 1-7 and the digit is added as the ones place,
    i.e. ``letter_index * 10 + digit``.

    Args:
        token: A two-character string like "A7".

    Returns:
        The numeric value of the token.

    Raises:
        ValueError: If the token is malformed.
    """
    if not _TOKEN_PATTERN.match(token):
        raise ValueError(f"Invalid Fluxon token: {token!r}")
    letter_index = ord(token[0]) - ord("A") + 1  # A=1, B=2, ..., G=7
    digit = int(token[1])
    return letter_index * 10 + digit


def _token_from_value(value: int) -> str:
    """Inverse of ``token_value``."""
    if value < 10 or value > 79:
        raise ValueError(f"Value out of token range: {value}")
    digit = value % 10
    letter_index = value // 10
    return chr(ord("A") + letter_index - 1) + str(digit)


# ---------------------------------------------------------------------------
# Packet parsing and formatting
# ---------------------------------------------------------------------------

def parse_fluxon_packet(packet: str) -> dict[str, Any]:
    """Parse a Fluxon packet string into a structured dictionary.

    Args:
        packet: A string like "FXN::2::alpha::A7-B3-C5::42".

    Returns:
        A dictionary with keys ``version`` (int), ``channel`` (str),
        ``payload`` (str), ``checksum`` (int), and ``tokens`` (list[str]).

    Raises:
        ValueError: If the packet format is invalid.
    """
    match = _PACKET_PATTERN.match(packet)
    if not match:
        raise ValueError(f"Invalid Fluxon packet format: {packet!r}")

    version = int(match.group("version"))
    channel = match.group("channel")
    payload = match.group("payload")
    checksum = int(match.group("checksum"))

    if version not in _VALID_VERSIONS:
        raise ValueError(f"Invalid version: {version}")
    if channel not in _VALID_CHANNELS:
        raise ValueError(f"Invalid channel: {channel}")

    tokens = split_fluxon_payload(payload)
    for token in tokens:
        if not _TOKEN_PATTERN.match(token):
            raise ValueError(f"Invalid token in payload: {token!r}")

    return {
        "version": version,
        "channel": channel,
        "payload": payload,
        "checksum": checksum,
        "tokens": tokens,
    }


def format_fluxon_packet(
    version: int, channel: str, payload: str, checksum: int | None = None
) -> str:
    """Format a Fluxon packet string from its components.

    If ``checksum`` is not provided, it is computed automatically from the
    payload and version.

    Args:
        version: The protocol version (1, 2, or 3).
        channel: One of "alpha", "beta", "gamma".
        payload: A dash-separated payload string.
        checksum: Optional checksum value.

    Returns:
        A formatted Fluxon packet string.
    """
    if checksum is None:
        checksum = compute_fluxon_checksum(payload, version)
    return f"FXN::{version}::{channel}::{payload}::{checksum}"


# ---------------------------------------------------------------------------
# Checksum and validation
# ---------------------------------------------------------------------------

def compute_fluxon_checksum(payload: str, version: int) -> int:
    """Compute the checksum of a payload for a given version.

    The checksum is ``sum(token_value(t) for t in tokens) % modulus`` where
    the modulus depends on the version (v1=89, v2=97, v3=113).

    Args:
        payload: A dash-separated payload string.
        version: The protocol version (1, 2, or 3).

    Returns:
        The computed checksum.
    """
    if version not in _VALID_VERSIONS:
        raise ValueError(f"Invalid version: {version}")
    tokens = split_fluxon_payload(payload)
    total = sum(token_value(t) for t in tokens)
    return total % _CHECKSUM_MODULUS[version]


def is_legacy_packet(packet: str | dict[str, Any]) -> bool:
    """Return whether a packet is a legacy (version 1) packet.

    Args:
        packet: Either a packet string or a parsed record.
    """
    if isinstance(packet, str):
        record = parse_fluxon_packet(packet)
    else:
        record = packet
    return record["version"] == 1


def validate_fluxon_packet(packet: str | dict[str, Any]) -> bool:
    """Validate a Fluxon packet's format and checksum.

    Legacy packets (version 1) are validated with the v1 modulus but are
    allowed to omit the checksum check when the payload is empty.

    Args:
        packet: Either a packet string or a parsed record.

    Returns:
        True if the packet is valid, False otherwise.
    """
    try:
        if isinstance(packet, str):
            record = parse_fluxon_packet(packet)
        else:
            record = packet
            # Validate token shapes even if already parsed.
            for token in record["tokens"]:
                if not _TOKEN_PATTERN.match(token):
                    return False

        expected = compute_fluxon_checksum(record["payload"], record["version"])
        if record["version"] == 1 and record["payload"] == "":
            return True
        return record["checksum"] == expected
    except (ValueError, KeyError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Channel normalization and frame decoding
# ---------------------------------------------------------------------------

def normalize_channel_value(raw: float, channel: str) -> float:
    """Normalize a raw numeric value according to the channel.

    * alpha: raw / 100
    * beta:  raw / 10
    * gamma: raw (unchanged)

    Args:
        raw: The raw numeric value.
        channel: One of "alpha", "beta", "gamma".

    Returns:
        The normalized value.
    """
    if channel not in _VALID_CHANNELS:
        raise ValueError(f"Invalid channel: {channel}")
    return raw / _CHANNEL_NORMALIZER[channel]


def decode_fluxon_frame(frame: str) -> str:
    """Decode a Fluxon frame into a packet string.

    A frame wraps a packet with a header and trailer::

        [FXN:<packet>:END]

    Args:
        frame: A frame string like "[FXN:FXN::2::alpha::A7::15:END]".

    Returns:
        The inner packet string.

    Raises:
        ValueError: If the frame format is invalid.
    """
    if not (frame.startswith("[FXN:") and frame.endswith(":END]")):
        raise ValueError(f"Invalid Fluxon frame: {frame!r}")
    inner = frame[5:-5]
    if not inner.startswith("FXN::"):
        raise ValueError(f"Frame does not contain a Fluxon packet: {frame!r}")
    return inner


# ---------------------------------------------------------------------------
# Record aggregation
# ---------------------------------------------------------------------------

def merge_fluxon_records(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge multiple parsed Fluxon records into a single summary record.

    The merged record concatenates payloads and tokens, keeps the most
    frequent channel, and uses the maximum version among inputs.

    Args:
        records: A list of parsed packet records.

    Returns:
        A merged record without a checksum.
    """
    if not records:
        raise ValueError("Cannot merge empty record list")

    payloads = []
    all_tokens: list[str] = []
    versions = []
    channels: list[str] = []

    for rec in records:
        payloads.append(rec["payload"])
        all_tokens.extend(rec["tokens"])
        versions.append(rec["version"])
        channels.append(rec["channel"])

    # Most frequent channel, tie-break by first occurrence.
    channel_counts = {}
    for ch in channels:
        channel_counts[ch] = channel_counts.get(ch, 0) + 1
    dominant_channel = max(channels, key=lambda c: (channel_counts[c], -channels.index(c)))

    merged_payload = "-".join(payloads) if any(payloads) else ""
    return {
        "version": max(versions),
        "channel": dominant_channel,
        "payload": merged_payload,
        "tokens": all_tokens,
        "checksum": None,
    }


def summarize_fluxon_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize a list of parsed Fluxon records.

    Args:
        records: A list of parsed packet records.

    Returns:
        A dictionary with ``count``, ``valid_count``, ``legacy_count``,
        ``channel_counts``, ``total_token_value``, and ``average_token_value``.
    """
    if not records:
        return {
            "count": 0,
            "valid_count": 0,
            "legacy_count": 0,
            "channel_counts": {},
            "total_token_value": 0,
            "average_token_value": 0.0,
        }

    valid_count = sum(1 for rec in records if validate_fluxon_packet(rec))
    legacy_count = sum(1 for rec in records if is_legacy_packet(rec))
    channel_counts: dict[str, int] = {}
    total_token_value = 0
    token_count = 0

    for rec in records:
        channel_counts[rec["channel"]] = channel_counts.get(rec["channel"], 0) + 1
        for token in rec["tokens"]:
            total_token_value += token_value(token)
            token_count += 1

    return {
        "count": len(records),
        "valid_count": valid_count,
        "legacy_count": legacy_count,
        "channel_counts": channel_counts,
        "total_token_value": total_token_value,
        "average_token_value": total_token_value / token_count if token_count else 0.0,
    }


# ---------------------------------------------------------------------------
# Repair utility
# ---------------------------------------------------------------------------

def repair_fluxon_packet(packet: str) -> str:
    """Attempt to repair a malformed Fluxon packet.

    Repairs performed:
        * Recompute an incorrect checksum.
        * Replace an invalid channel with "alpha".
        * Drop malformed tokens from the payload.
        * Clamp an invalid version to 2.

    Args:
        packet: A packet string.

    Returns:
        A repaired packet string, or the original string if no repair applies.
    """
    try:
        rec = parse_fluxon_packet(packet)
        if not validate_fluxon_packet(rec):
            rec["checksum"] = compute_fluxon_checksum(rec["payload"], rec["version"])
        return format_fluxon_packet(
            rec["version"], rec["channel"], rec["payload"], rec["checksum"]
        )
    except ValueError:
        pass

    # Fallback structural repair.
    parts = packet.split("::")
    if len(parts) != 5 or not parts[0].startswith("FXN"):
        return packet

    try:
        version = int(parts[1])
    except ValueError:
        version = 2
    if version not in _VALID_VERSIONS:
        version = 2

    channel = parts[2] if parts[2] in _VALID_CHANNELS else "alpha"

    raw_tokens = parts[3].split("-")
    cleaned_tokens = [t for t in raw_tokens if _TOKEN_PATTERN.match(t)]
    payload = "-".join(cleaned_tokens)

    try:
        checksum = int(parts[4])
    except ValueError:
        checksum = compute_fluxon_checksum(payload, version)

    expected = compute_fluxon_checksum(payload, version)
    if checksum != expected:
        checksum = expected

    return format_fluxon_packet(version, channel, payload, checksum)


# ---------------------------------------------------------------------------
# Extended functions for the full-scale benchmark
# ---------------------------------------------------------------------------


def serialize_fluxon_records(records: list[dict[str, Any]]) -> str:
    """Serialize a list of parsed Fluxon records into a wire string.

    Format (fictional): records are separated by ``|``; each record is
    ``version,channel,payload,checksum``.

    Args:
        records: Parsed packet records.

    Returns:
        A serialized string.
    """
    parts = []
    for rec in records:
        payload = rec["payload"].replace(",", "\\,")
        parts.append(f"{rec['version']},{rec['channel']},{payload},{rec['checksum']}")
    return "FXR[" + "|".join(parts) + "]"


def deserialize_fluxon_records(serialized: str) -> list[dict[str, Any]]:
    """Deserialize a wire string produced by ``serialize_fluxon_records``.

    Args:
        serialized: A serialized record string.

    Returns:
        A list of parsed records.
    """
    if not (serialized.startswith("FXR[") and serialized.endswith("]")):
        raise ValueError(f"Invalid serialized Fluxon records: {serialized!r}")
    inner = serialized[4:-1]
    if not inner:
        return []
    records = []
    for part in inner.split("|"):
        # Split on unescaped commas.
        fields = []
        current = ""
        i = 0
        while i < len(part):
            if part[i] == "\\" and i + 1 < len(part) and part[i + 1] == ",":
                current += ","
                i += 2
            elif part[i] == ",":
                fields.append(current)
                current = ""
                i += 1
            else:
                current += part[i]
                i += 1
        fields.append(current)
        if len(fields) != 4:
            raise ValueError(f"Invalid record segment: {part!r}")
        version = int(fields[0])
        channel = fields[1]
        payload = fields[2]
        checksum = int(fields[3])
        record = {
            "version": version,
            "channel": channel,
            "payload": payload,
            "checksum": checksum,
            "tokens": split_fluxon_payload(payload),
        }
        if not validate_fluxon_packet(record):
            raise ValueError(f"Deserialized record has invalid checksum: {part!r}")
        records.append(record)
    return records


def compare_fluxon_packets(packet1: str, packet2: str) -> dict[str, Any]:
    """Compare two Fluxon packets and return a structured diff.

    Returns:
        A dictionary with ``same_version``, ``same_channel``, ``same_payload``,
        ``same_checksum``, ``token_sum_diff``.
    """
    rec1 = parse_fluxon_packet(packet1)
    rec2 = parse_fluxon_packet(packet2)
    return {
        "same_version": rec1["version"] == rec2["version"],
        "same_channel": rec1["channel"] == rec2["channel"],
        "same_payload": rec1["payload"] == rec2["payload"],
        "same_checksum": rec1["checksum"] == rec2["checksum"],
        "token_sum_diff": sum(token_value(t) for t in rec1["tokens"])
        - sum(token_value(t) for t in rec2["tokens"]),
    }


def filter_fluxon_by_channel(
    records: list[dict[str, Any]], channel: str
) -> list[dict[str, Any]]:
    """Return only records matching the given channel."""
    if channel not in _VALID_CHANNELS:
        raise ValueError(f"Invalid channel: {channel}")
    return [rec for rec in records if rec["channel"] == channel]


def sort_fluxon_records(
    records: list[dict[str, Any]], key: str = "version"
) -> list[dict[str, Any]]:
    """Sort Fluxon records by a given key.

    Supported keys: ``version``, ``channel``, ``token_sum``.
    """
    if key == "version":
        return sorted(records, key=lambda r: r["version"])
    if key == "channel":
        return sorted(records, key=lambda r: r["channel"])
    if key == "token_sum":
        return sorted(
            records, key=lambda r: sum(token_value(t) for t in r["tokens"])
        )
    raise ValueError(f"Unsupported sort key: {key}")


def compute_fluxon_hash(payload: str, version: int) -> int:
    """Compute an alternative Fluxon hash (not the checksum).

    The hash is ``sum(token_value(t) ** 2 for t in tokens) % modulus``.

    Args:
        payload: A dash-separated payload string.
        version: The protocol version (1, 2, or 3).

    Returns:
        The computed hash.
    """
    if version not in _VALID_VERSIONS:
        raise ValueError(f"Invalid version: {version}")
    tokens = split_fluxon_payload(payload)
    total = sum(token_value(t) ** 2 for t in tokens)
    return total % _CHECKSUM_MODULUS[version]


def apply_fluxon_transformation(payload: str, transform: str) -> str:
    """Apply a fictional transformation to a payload.

    Supported transforms:
        * ``reverse`` - reverse the order of tokens.
        * ``swap`` - swap letter and digit in each token.
        * ``increment`` - increment the digit in each token by 1 (mod 10).

    Args:
        payload: A dash-separated payload string.
        transform: The transformation name.

    Returns:
        The transformed payload string.
    """
    tokens = split_fluxon_payload(payload)
    if transform == "reverse":
        return "-".join(reversed(tokens))
    if transform == "swap":
        new_tokens = []
        for t in tokens:
            if not _TOKEN_PATTERN.match(t):
                raise ValueError(f"Invalid token: {t!r}")
            new_tokens.append(t[1] + t[0])
        return "-".join(new_tokens)
    if transform == "increment":
        new_tokens = []
        for t in tokens:
            if not _TOKEN_PATTERN.match(t):
                raise ValueError(f"Invalid token: {t!r}")
            letter = t[0]
            digit = (int(t[1]) + 1) % 10
            new_tokens.append(f"{letter}{digit}")
        return "-".join(new_tokens)
    raise ValueError(f"Unsupported transform: {transform}")


def validate_fluxon_batch(packets: list[str]) -> list[bool]:
    """Validate a batch of packet strings.

    Args:
        packets: A list of packet strings.

    Returns:
        A parallel list of boolean validation results.
    """
    return [validate_fluxon_packet(p) for p in packets]


def group_fluxon_by_channel(
    records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group parsed records by their channel."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        groups.setdefault(rec["channel"], []).append(rec)
    return groups
