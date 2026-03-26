"""Tests for the B2 magic commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from IPython.testing.globalipapp import get_ipython

from b2_jupyter.magics.b2_magics import B2Magics, _parse_args


@pytest.fixture
def ip():
    """Get a test IPython shell instance."""
    shell = get_ipython()
    if shell is None:
        pytest.skip("IPython shell not available")
    return shell


@pytest.fixture
def magics(ip):
    """Create a B2Magics instance with test shell."""
    m = B2Magics(ip)
    return m


class TestParseArgs:
    """Tests for argument parsing."""

    def test_simple_args(self):
        assert _parse_args("ls my-bucket") == ["ls", "my-bucket"]

    def test_quoted_args(self):
        assert _parse_args('upload "my file.csv" bucket/path') == [
            "upload",
            "my file.csv",
            "bucket/path",
        ]

    def test_empty_line(self):
        assert _parse_args("") == []

    def test_flags(self):
        assert _parse_args("ls bucket/ --recursive") == ["ls", "bucket/", "--recursive"]

    def test_key_value_flags(self):
        assert _parse_args("auth --key-id abc --key def") == [
            "auth",
            "--key-id",
            "abc",
            "--key",
            "def",
        ]


class TestB2MagicsDispatch:
    """Tests for the %b2 dispatcher."""

    def test_help_on_empty(self, magics, capsys):
        magics.b2("")
        captured = capsys.readouterr()
        assert "B2 Jupyter Magic Commands" in captured.out

    def test_unknown_subcommand(self, magics, capsys):
        magics.b2("nonexistent")
        captured = capsys.readouterr()
        assert "Unknown subcommand" in captured.err

    def test_help_subcommand(self, magics, capsys):
        magics.b2("help")
        captured = capsys.readouterr()
        assert "Authentication" in captured.out
        assert "%b2 auth" in captured.out


class TestB2LoadMagic:
    """Tests for %b2_load."""

    def test_no_args(self, magics, capsys):
        result = magics.b2_load("")
        assert result is None
        captured = capsys.readouterr()
        assert "Usage" in captured.err

    def test_bucket_only_without_key(self, magics, capsys):
        # Mock auth to avoid real API calls
        magics._auth._api = MagicMock()
        result = magics.b2_load("my-bucket")
        assert result is None
        captured = capsys.readouterr()
        assert "file path" in captured.err


class TestB2SaveMagic:
    """Tests for %%b2_save."""

    def test_no_args(self, magics, capsys):
        magics.b2_save("", "df")
        captured = capsys.readouterr()
        assert "Usage" in captured.err

    def test_bucket_only(self, magics, capsys):
        magics.b2_save("my-bucket", "df")
        captured = capsys.readouterr()
        assert "full file path" in captured.err


class TestSerializeForUpload:
    """Tests for _serialize_for_upload."""

    def test_bytes_passthrough(self, magics):
        data = b"hello world"
        result = magics._serialize_for_upload(data, "file.bin")
        assert result == data

    def test_string_encoding(self, magics):
        result = magics._serialize_for_upload("hello", "file.txt")
        assert result == b"hello"

    def test_dict_as_json(self, magics):
        import json

        obj = {"key": "value", "num": 42}
        result = magics._serialize_for_upload(obj, "data.json")
        parsed = json.loads(result)
        assert parsed == obj

    def test_list_as_json(self, magics):
        import json

        obj = [1, 2, 3]
        result = magics._serialize_for_upload(obj, "data.json")
        parsed = json.loads(result)
        assert parsed == obj
