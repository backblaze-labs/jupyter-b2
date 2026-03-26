"""Tests for the data loading utilities."""

from __future__ import annotations

import pytest

from b2_jupyter.magics.loaders import _detect_format, _parse_b2_path


class TestParseB2Path:
    """Tests for _parse_b2_path."""

    def test_simple_bucket_and_key(self):
        assert _parse_b2_path("my-bucket/data/file.csv") == ("my-bucket", "data/file.csv")

    def test_b2_protocol_prefix(self):
        assert _parse_b2_path("b2://my-bucket/data/file.csv") == ("my-bucket", "data/file.csv")

    def test_bucket_only(self):
        assert _parse_b2_path("my-bucket") == ("my-bucket", "")

    def test_b2_protocol_bucket_only(self):
        assert _parse_b2_path("b2://my-bucket") == ("my-bucket", "")

    def test_deep_path(self):
        assert _parse_b2_path("bucket/a/b/c/d/file.parquet") == (
            "bucket",
            "a/b/c/d/file.parquet",
        )

    def test_path_with_spaces(self):
        assert _parse_b2_path("bucket/my data/file name.csv") == (
            "bucket",
            "my data/file name.csv",
        )


class TestDetectFormat:
    """Tests for _detect_format."""

    @pytest.mark.parametrize(
        "file_key, expected",
        [
            ("data.csv", ".csv"),
            ("data.parquet", ".parquet"),
            ("data.json", ".json"),
            ("data.jsonl", ".jsonl"),
            ("data.tsv", ".tsv"),
            ("data.feather", ".feather"),
            ("data.orc", ".orc"),
            ("data.xlsx", ".xlsx"),
            ("path/to/data.CSV", ".csv"),
            ("data.tar.gz", ".gz"),
            ("noextension", ""),
        ],
    )
    def test_format_detection(self, file_key: str, expected: str):
        assert _detect_format(file_key) == expected
