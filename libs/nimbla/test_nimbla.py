"""Unit tests for the Nimbla Time Series Toolkit."""

import pytest

import nimbla


def test_nimbla_value():
    assert nimbla.nimbla_value("A7") == 1.7
    assert nimbla.nimbla_value("B3") == 2.3
    assert nimbla.nimbla_value("G9") == 7.9


def test_parse_nimbla_series():
    rec = nimbla.parse_nimbla_series("NIM|1:A1,2:B2,3:C3")
    assert rec["timestamps"] == [1, 2, 3]
    assert rec["values"] == pytest.approx([1.1, 2.2, 3.3])


def test_parse_nimbla_series_invalid_order():
    with pytest.raises(ValueError):
        nimbla.parse_nimbla_series("NIM|3:A1,2:B2")


def test_format_nimbla_series():
    series = {"timestamps": [1, 2], "values": [1.7, 2.3]}
    assert nimbla.format_nimbla_series(series["timestamps"], series["values"]) == "NIM|1:A7,2:B3"


def test_moving_average():
    series = {"timestamps": [1, 2, 3], "values": [1.0, 2.0, 3.0]}
    assert nimbla.moving_average(series, 2) == pytest.approx([1.0, 1.5, 2.5])


def test_detect_outliers():
    series = {"timestamps": [1, 2, 3], "values": [1.0, 5.0, 1.5]}
    assert nimbla.detect_outliers(series, 3.0) == [2]


def test_normalize_nimbla_minmax():
    series = {"timestamps": [1, 2, 3], "values": [1.0, 2.0, 3.0]}
    assert nimbla.normalize_nimbla(series, "minmax") == pytest.approx([0.0, 0.5, 1.0])


def test_normalize_nimbla_zscore():
    series = {"timestamps": [1, 2, 3], "values": [1.0, 2.0, 3.0]}
    assert nimbla.normalize_nimbla(series, "zscore") == pytest.approx([-1.22474487139, 0.0, 1.22474487139])


def test_merge_nimbla_series():
    s1 = {"timestamps": [1, 3], "values": [1.0, 3.0]}
    s2 = {"timestamps": [2, 3], "values": [2.0, 4.0]}
    merged = nimbla.merge_nimbla_series(s1, s2)
    assert merged["timestamps"] == [1, 2, 3]
    assert merged["values"] == pytest.approx([1.0, 2.0, 4.0])


def test_forecast_next():
    series = {"timestamps": [1, 2, 3], "values": [1.0, 2.0, 3.0]}
    assert nimbla.forecast_next(series, "last") == 3.0
    assert nimbla.forecast_next(series, "mean") == 2.0
    assert nimbla.forecast_next(series, "diff") == 4.0


def test_summarize_nimbla():
    series = {"timestamps": [1, 2, 3], "values": [1.0, 2.0, 3.0]}
    summary = nimbla.summarize_nimbla(series)
    assert summary["count"] == 3
    assert summary["mean"] == 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
