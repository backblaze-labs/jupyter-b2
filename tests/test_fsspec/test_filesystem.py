"""Tests for the B2 fsspec filesystem."""

from __future__ import annotations

import pytest

from b2_jupyter.fsspec_backend.filesystem import B2FileSystem


class TestSplitPath:
    """Tests for B2FileSystem._split_path."""

    def test_bucket_and_key(self):
        assert B2FileSystem._split_path("my-bucket/path/to/file.csv") == (
            "my-bucket",
            "path/to/file.csv",
        )

    def test_bucket_only(self):
        assert B2FileSystem._split_path("my-bucket") == ("my-bucket", "")

    def test_leading_slash(self):
        assert B2FileSystem._split_path("/my-bucket/file.csv") == ("my-bucket", "file.csv")

    def test_trailing_slash_stripped(self):
        assert B2FileSystem._split_path("my-bucket/prefix/") == ("my-bucket", "prefix")

    def test_deep_path(self):
        assert B2FileSystem._split_path("bucket/a/b/c/d.parquet") == (
            "bucket",
            "a/b/c/d.parquet",
        )


class TestB2FileSystemInit:
    """Tests for B2FileSystem initialization."""

    def test_missing_credentials_raises(self):
        with pytest.raises(ValueError, match="B2 credentials required"):
            B2FileSystem()

    def test_missing_fsspec_import(self, monkeypatch):
        """Test error message when fsspec is not installed."""
        import b2_jupyter.fsspec_backend.filesystem as mod

        monkeypatch.setattr(mod, "HAS_FSSPEC", False)
        with pytest.raises(ImportError, match="fsspec is required"):
            B2FileSystem(key_id="test", app_key="test")
