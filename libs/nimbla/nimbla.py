"""Nimbla Time Series Toolkit.

A synthetic, fictional library for parsing and processing time-series data.
The Nimbla format is made up and unrelated to real-world formats so that
pretrained models cannot rely on memorized parsing rules.

Series format::

    NIM|<timestamp>:<token>,<timestamp>:<token>,...

Examples:

    NIM|1:A1,2:B2,3:C3
    NIM|10:G9,11:A0

Rules:
    * timestamps are positive integers in ascending order.
    * tokens are an uppercase letter A-G followed by a single digit 0-9.
    * ``nimbla_value`` converts a token to a numeric value.
"""

from __future__ import annotations

import math
import re
from typing import Any


_TOKEN_PATTERN = re.compile(r"^[A-G][0-9]$")
_SERIES_PATTERN = re.compile(r"^NIM\|(?P<entries>.*)$")
_ENTRY_PATTERN = re.compile(r"^(?P<ts>\d+):(?P<token>[A-G][0-9])$")


def nimbla_value(token: str) -> float:
    """Convert a Nimbla token to a numeric value.

    The letter A-G maps to 1-7 and the digit is the fractional part,
    i.e. ``letter_index + digit / 10``.

    Args:
        token: A two-character string like "A7".

    Returns:
        The numeric value (e.g. "A7" -> 1.7, "B3" -> 2.3).
    """
    if not _TOKEN_PATTERN.match(token):
        raise ValueError(f"Invalid Nimbla token: {token!r}")
    letter_index = ord(token[0]) - ord("A") + 1
    digit = int(token[1])
    return letter_index + digit / 10.0


def _token_from_value(value: float) -> str:
    """Inverse of ``nimbla_value`` (within token range)."""
    if value < 1.0 or value > 7.9:
        raise ValueError(f"Value out of Nimbla token range: {value}")
    letter_index = int(value)
    digit = int(round((value - letter_index) * 10))
    return chr(ord("A") + letter_index - 1) + str(digit)


def parse_nimbla_series(series: str) -> dict[str, Any]:
    """Parse a Nimbla series string into a structured dictionary.

    Returns:
        A dictionary with ``timestamps`` (list[int]) and ``values`` (list[float]).
    """
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
        ts = int(em.group("ts"))
        token = em.group("token")
        if timestamps and ts <= timestamps[-1]:
            raise ValueError(f"Timestamps must be strictly increasing: {series!r}")
        timestamps.append(ts)
        values.append(nimbla_value(token))
    return {"timestamps": timestamps, "values": values}


def format_nimbla_series(timestamps: list[int], values: list[float]) -> str:
    """Format timestamps and values back into a Nimbla series string."""
    if len(timestamps) != len(values):
        raise ValueError("Timestamps and values must have the same length")
    entries = [f"{ts}:{_token_from_value(v)}" for ts, v in zip(timestamps, values)]
    return "NIM|" + ",".join(entries)


def moving_average(series: dict[str, Any], window_size: int) -> list[float]:
    """Compute the simple moving average of a series.

    The first ``window_size - 1`` entries yield averages over the available
    prefix (partial window).
    """
    values = series["values"]
    if window_size <= 0:
        raise ValueError("window_size must be positive")
    result = []
    for i in range(len(values)):
        start = max(0, i - window_size + 1)
        window = values[start : i + 1]
        result.append(sum(window) / len(window))
    return result


def detect_outliers(series: dict[str, Any], threshold: float) -> list[int]:
    """Return timestamps whose values exceed ``threshold``."""
    return [
        ts
        for ts, value in zip(series["timestamps"], series["values"])
        if value > threshold
    ]


def normalize_nimbla(series: dict[str, Any], method: str = "minmax") -> list[float]:
    """Normalize series values.

    Methods:
        * ``minmax`` - scale to [0, 1] using min/max.
        * ``zscore`` - subtract mean and divide by std.
    """
    values = series["values"]
    if not values:
        return []
    if method == "minmax":
        min_v = min(values)
        max_v = max(values)
        if max_v == min_v:
            return [0.0] * len(values)
        return [(v - min_v) / (max_v - min_v) for v in values]
    if method == "zscore":
        mean = sum(values) / len(values)
        std = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
        if std == 0:
            return [0.0] * len(values)
        return [(v - mean) / std for v in values]
    raise ValueError(f"Unsupported normalization method: {method}")


def merge_nimbla_series(
    series1: dict[str, Any], series2: dict[str, Any]
) -> dict[str, Any]:
    """Merge two Nimbla series by timestamp, keeping the later value on conflict."""
    merged: dict[int, float] = {}
    for ts, value in zip(series1["timestamps"], series1["values"]):
        merged[ts] = value
    for ts, value in zip(series2["timestamps"], series2["values"]):
        # Later series wins on timestamp conflict.
        merged[ts] = value
    sorted_ts = sorted(merged)
    return {"timestamps": sorted_ts, "values": [merged[ts] for ts in sorted_ts]}


def forecast_next(series: dict[str, Any], method: str = "last") -> float:
    """Forecast the next value after the last observed timestamp.

    Methods:
        * ``last`` - repeat the last value.
        * ``mean`` - average of all values.
        * ``diff`` - add the average first difference to the last value.
    """
    values = series["values"]
    if not values:
        raise ValueError("Cannot forecast an empty series")
    if method == "last":
        return values[-1]
    if method == "mean":
        return sum(values) / len(values)
    if method == "diff":
        if len(values) == 1:
            return values[-1]
        diffs = [values[i] - values[i - 1] for i in range(1, len(values))]
        return values[-1] + (sum(diffs) / len(diffs))
    raise ValueError(f"Unsupported forecast method: {method}")


def summarize_nimbla(series: dict[str, Any]) -> dict[str, Any]:
    """Return a statistical summary of a Nimbla series."""
    values = series["values"]
    if not values:
        return {
            "count": 0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "std": 0.0,
        }
    mean = sum(values) / len(values)
    std = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": mean,
        "std": std,
    }


def series_length(series: dict[str, Any]) -> int:
    """Return the number of entries in a Nimbla series."""
    return len(series["values"])


def first_timestamp(series: dict[str, Any]) -> int:
    """Return the first timestamp of a series, or 0 if empty."""
    if not series["timestamps"]:
        return 0
    return series["timestamps"][0]


def last_timestamp(series: dict[str, Any]) -> int:
    """Return the last timestamp of a series, or 0 if empty."""
    if not series["timestamps"]:
        return 0
    return series["timestamps"][-1]


def first_value(series: dict[str, Any]) -> float:
    """Return the first value of a series, or 0.0 if empty."""
    if not series["values"]:
        return 0.0
    return series["values"][0]


def last_value(series: dict[str, Any]) -> float:
    """Return the last value of a series, or 0.0 if empty."""
    if not series["values"]:
        return 0.0
    return series["values"][-1]


def value_differences(series: dict[str, Any]) -> list[float]:
    """Return consecutive differences between series values."""
    values = series["values"]
    return [values[i] - values[i - 1] for i in range(1, len(values))]


def select_nimbla_range(
    series: dict[str, Any], start: int, end: int
) -> dict[str, Any]:
    """Return the sub-series with timestamps in the inclusive range [start, end]."""
    timestamps = []
    values = []
    for ts, value in zip(series["timestamps"], series["values"]):
        if start <= ts <= end:
            timestamps.append(ts)
            values.append(value)
    return {"timestamps": timestamps, "values": values}


def scale_nimbla(series: dict[str, Any], factor: float) -> list[float]:
    """Multiply every value in the series by factor."""
    return [v * factor for v in series["values"]]
