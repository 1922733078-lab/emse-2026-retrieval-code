"""Buggy distractor variants of Nimbla functions."""

from __future__ import annotations

import math
import re
from typing import Any


_TOKEN_PATTERN = re.compile(r"^[A-G][0-9]$")
_SERIES_PATTERN = re.compile(r"^NIM\|(?P<entries>.*)$")
_ENTRY_PATTERN = re.compile(r"^(?P<ts>\d+):(?P<token>[A-G][0-9])$")


def nimbla_value_fluxon_style(token: str) -> float:
    """Convert a Nimbla token using Fluxon-style value (letter * 10 + digit)."""
    if not _TOKEN_PATTERN.match(token):
        raise ValueError(f"Invalid Nimbla token: {token!r}")
    letter_index = ord(token[0]) - ord("A") + 1
    digit = int(token[1])
    return letter_index * 10 + digit


def parse_nimbla_series_descending(series: str) -> dict[str, Any]:
    """Parse a series but allow descending timestamps (boundary bug)."""
    match = _SERIES_PATTERN.match(series.strip())
    if not match:
        raise ValueError(f"Invalid Nimbla series: {series!r}")
    entries = match.group("entries").split(",")
    timestamps: list[int] = []
    values: list[float] = []
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        em = _ENTRY_PATTERN.match(entry)
        if not em:
            raise ValueError(f"Invalid Nimbla entry: {entry!r}")
        timestamps.append(int(em.group("ts")))
        values.append(nimbla_value_fluxon_style(em.group("token")))
    return {"timestamps": timestamps, "values": values}


def moving_average_off_by_one(series: dict[str, Any], window_size: int) -> list[float]:
    """Compute moving average with an extra-wide window (off-by-one bug)."""
    values = series["values"]
    window_size = window_size + 1
    result = []
    for i in range(len(values)):
        start = max(0, i - window_size + 1)
        window = values[start : i + 1]
        result.append(sum(window) / len(window))
    return result


def detect_outliers_below_threshold(series: dict[str, Any], threshold: float) -> list[int]:
    """Return timestamps whose values are below the threshold (inverted logic)."""
    return [
        ts
        for ts, value in zip(series["timestamps"], series["values"])
        if value < threshold
    ]


def normalize_nimbla_minmax_inverted(series: dict[str, Any], method: str = "minmax") -> list[float]:
    """Apply inverted min-max scaling: (max - v) / (max - min)."""
    values = series["values"]
    if not values:
        return []
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return [0.0] * len(values)
    return [(max_v - v) / (max_v - min_v) for v in values]


def merge_nimbla_series_first_wins(
    series1: dict[str, Any], series2: dict[str, Any]
) -> dict[str, Any]:
    """Merge series but first series wins on timestamp conflicts."""
    merged: dict[int, float] = {}
    for ts, value in zip(series2["timestamps"], series2["values"]):
        merged[ts] = value
    for ts, value in zip(series1["timestamps"], series1["values"]):
        merged[ts] = value
    sorted_ts = sorted(merged)
    return {"timestamps": sorted_ts, "values": [merged[ts] for ts in sorted_ts]}


def forecast_next_zero(series: dict[str, Any], method: str = "last") -> float:
    """Always forecast 0.0 regardless of series."""
    return 0.0


def summarize_nimbla_count_only(series: dict[str, Any]) -> dict[str, Any]:
    """Return a summary with only the count (missing statistics)."""
    return {
        "count": len(series["values"]),
        "min": 0.0,
        "max": 0.0,
        "mean": 0.0,
        "std": 0.0,
    }
