"""Unit tests for the Fluxon Protocol Toolkit."""

import pytest

import fluxon


def test_split_fluxon_payload_basic():
    assert fluxon.split_fluxon_payload("A7-B3-C5") == ["A7", "B3", "C5"]


def test_split_fluxon_payload_empty():
    assert fluxon.split_fluxon_payload("") == []


def test_token_value():
    assert fluxon.token_value("A7") == 17
    assert fluxon.token_value("B3") == 23
    assert fluxon.token_value("G9") == 79


def test_token_value_invalid():
    with pytest.raises(ValueError):
        fluxon.token_value("H7")
    with pytest.raises(ValueError):
        fluxon.token_value("A12")


def test_parse_fluxon_packet():
    rec = fluxon.parse_fluxon_packet("FXN::2::alpha::A7-B3-C5::42")
    assert rec["version"] == 2
    assert rec["channel"] == "alpha"
    assert rec["payload"] == "A7-B3-C5"
    assert rec["tokens"] == ["A7", "B3", "C5"]


def test_parse_fluxon_packet_invalid_version():
    with pytest.raises(ValueError):
        fluxon.parse_fluxon_packet("FXN::4::alpha::A7::42")


def test_parse_fluxon_packet_invalid_channel():
    with pytest.raises(ValueError):
        fluxon.parse_fluxon_packet("FXN::2::delta::A7::42")


def test_compute_fluxon_checksum():
    payload = "A7-B3-C5"  # values: 17, 23, 35 -> total 75
    assert fluxon.compute_fluxon_checksum(payload, 1) == 75 % 89
    assert fluxon.compute_fluxon_checksum(payload, 2) == 75 % 97
    assert fluxon.compute_fluxon_checksum(payload, 3) == 75 % 113


def test_validate_fluxon_packet():
    payload = "A7-B3"
    checksum = fluxon.compute_fluxon_checksum(payload, 2)
    packet = f"FXN::2::alpha::{payload}::{checksum}"
    assert fluxon.validate_fluxon_packet(packet) is True


def test_validate_fluxon_packet_wrong_checksum():
    assert fluxon.validate_fluxon_packet("FXN::2::alpha::A7-B3::0") is False


def test_is_legacy_packet():
    assert fluxon.is_legacy_packet("FXN::1::beta::A2::15") is True
    assert fluxon.is_legacy_packet("FXN::2::beta::A2::15") is False


def test_normalize_channel_value():
    assert fluxon.normalize_channel_value(100.0, "alpha") == 1.0
    assert fluxon.normalize_channel_value(100.0, "beta") == 10.0
    assert fluxon.normalize_channel_value(100.0, "gamma") == 100.0


def test_decode_fluxon_frame():
    packet = "FXN::2::alpha::A7::15"
    frame = f"[FXN:{packet}:END]"
    assert fluxon.decode_fluxon_frame(frame) == packet


def test_decode_fluxon_frame_invalid():
    with pytest.raises(ValueError):
        fluxon.decode_fluxon_frame("FXN::2::alpha::A7::15")


def test_format_fluxon_packet():
    packet = fluxon.format_fluxon_packet(2, "beta", "A7-B3")
    assert packet.startswith("FXN::2::beta::A7-B3::")
    assert fluxon.validate_fluxon_packet(packet)


def test_merge_fluxon_records():
    r1 = fluxon.parse_fluxon_packet("FXN::1::alpha::A7::15")
    r2 = fluxon.parse_fluxon_packet("FXN::2::beta::B3::23")
    merged = fluxon.merge_fluxon_records([r1, r2])
    assert merged["version"] == 2
    assert merged["payload"] == "A7-B3"
    assert merged["tokens"] == ["A7", "B3"]


def test_summarize_fluxon_records():
    r1 = fluxon.parse_fluxon_packet("FXN::1::alpha::A7::17")
    r2 = fluxon.parse_fluxon_packet("FXN::2::beta::B3::23")
    summary = fluxon.summarize_fluxon_records([r1, r2])
    assert summary["count"] == 2
    assert summary["valid_count"] == 2
    assert summary["legacy_count"] == 1
    assert summary["channel_counts"]["alpha"] == 1
    assert summary["channel_counts"]["beta"] == 1


def test_repair_fluxon_packet_checksum():
    payload = "A7-B3"
    correct_checksum = fluxon.compute_fluxon_checksum(payload, 2)
    repaired = fluxon.repair_fluxon_packet(f"FXN::2::alpha::{payload}::0")
    assert repaired == f"FXN::2::alpha::{payload}::{correct_checksum}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ---------------------------------------------------------------------------
# Extended function tests
# ---------------------------------------------------------------------------


def test_serialize_deserialize_roundtrip():
    p1 = fluxon.format_fluxon_packet(1, "alpha", "A7")
    p2 = fluxon.format_fluxon_packet(2, "beta", "B3-C5")
    r1 = fluxon.parse_fluxon_packet(p1)
    r2 = fluxon.parse_fluxon_packet(p2)
    serialized = fluxon.serialize_fluxon_records([r1, r2])
    records = fluxon.deserialize_fluxon_records(serialized)
    assert len(records) == 2
    assert records[0]["version"] == 1
    assert records[1]["channel"] == "beta"


def test_compare_fluxon_packets():
    p1 = "FXN::2::alpha::A7::15"
    p2 = "FXN::2::alpha::B3::23"
    diff = fluxon.compare_fluxon_packets(p1, p2)
    assert diff["same_version"] is True
    assert diff["same_channel"] is True
    assert diff["same_payload"] is False


def test_filter_fluxon_by_channel():
    records = [
        fluxon.parse_fluxon_packet("FXN::1::alpha::A7::17"),
        fluxon.parse_fluxon_packet("FXN::2::beta::B3::23"),
    ]
    assert len(fluxon.filter_fluxon_by_channel(records, "alpha")) == 1


def test_sort_fluxon_records_by_token_sum():
    records = [
        fluxon.parse_fluxon_packet("FXN::2::alpha::G9::79"),
        fluxon.parse_fluxon_packet("FXN::1::beta::A1::11"),
    ]
    sorted_recs = fluxon.sort_fluxon_records(records, "token_sum")
    assert sorted_recs[0]["payload"] == "A1"


def test_compute_fluxon_hash():
    payload = "A7-B3"  # values 17, 23
    assert fluxon.compute_fluxon_hash(payload, 2) == (17 ** 2 + 23 ** 2) % 97


def test_apply_fluxon_transformation_reverse():
    assert fluxon.apply_fluxon_transformation("A7-B3", "reverse") == "B3-A7"


def test_apply_fluxon_transformation_swap():
    assert fluxon.apply_fluxon_transformation("A7-B3", "swap") == "7A-3B"


def test_apply_fluxon_transformation_increment():
    assert fluxon.apply_fluxon_transformation("A7-B9", "increment") == "A8-B0"


def test_validate_fluxon_batch():
    p1 = fluxon.format_fluxon_packet(2, "alpha", "A7")
    p2 = "FXN::2::alpha::A7::0"
    assert fluxon.validate_fluxon_batch([p1, p2]) == [True, False]


def test_group_fluxon_by_channel():
    records = [
        fluxon.parse_fluxon_packet("FXN::1::alpha::A7::17"),
        fluxon.parse_fluxon_packet("FXN::2::beta::B3::23"),
        fluxon.parse_fluxon_packet("FXN::3::alpha::C5::35"),
    ]
    groups = fluxon.group_fluxon_by_channel(records)
    assert len(groups["alpha"]) == 2
    assert len(groups["beta"]) == 1
