"""Tests for the rich display formatters."""

from __future__ import annotations

from unittest.mock import patch

from jupyter_b2.magics.display import (
    _format_timestamp,
    _human_size,
    display_auth_status,
    display_buckets,
    display_download_success,
    display_file_info,
    display_file_list,
    display_upload_success,
)


class TestHumanSize:
    """Tests for _human_size."""

    def test_bytes(self):
        assert _human_size(0) == "0.0 B"
        assert _human_size(512) == "512.0 B"

    def test_kilobytes(self):
        assert _human_size(1024) == "1.0 KB"
        assert _human_size(1536) == "1.5 KB"

    def test_megabytes(self):
        assert _human_size(1024 * 1024) == "1.0 MB"

    def test_gigabytes(self):
        assert _human_size(1024**3) == "1.0 GB"

    def test_terabytes(self):
        assert _human_size(1024**4) == "1.0 TB"


class TestFormatTimestamp:
    """Tests for _format_timestamp."""

    def test_none(self):
        assert _format_timestamp(None) == "—"

    def test_epoch_zero(self):
        result = _format_timestamp(0)
        assert "1970-01-01" in result

    def test_known_timestamp(self):
        # 2024-01-01 00:00:00 UTC = 1704067200000 ms
        result = _format_timestamp(1704067200000)
        assert "2024-01-01" in result
        assert "UTC" in result


class TestDisplayFunctions:
    """Tests for display_* functions — verify they produce HTML without errors."""

    @patch("jupyter_b2.magics.display.display")
    def test_display_file_list_empty(self, mock_display):
        display_file_list([], "my-bucket", "")
        mock_display.assert_called_once()
        html = mock_display.call_args[0][0]
        assert "No files found" in html.data

    @patch("jupyter_b2.magics.display.display")
    def test_display_file_list_with_files(self, mock_display):
        files = [
            {"name": "data.csv", "size": 1024, "uploadTimestamp": 1704067200000},
            {"name": "models/", "size": 0, "uploadTimestamp": None},
        ]
        display_file_list(files, "my-bucket", "")
        html = mock_display.call_args[0][0]
        assert "data.csv" in html.data
        assert "models/" in html.data
        assert "2 items" in html.data

    @patch("jupyter_b2.magics.display.display")
    def test_display_file_list_strips_prefix(self, mock_display):
        files = [{"name": "prefix/file.txt", "size": 100, "uploadTimestamp": None}]
        display_file_list(files, "bucket", "prefix/")
        html = mock_display.call_args[0][0]
        assert "file.txt" in html.data

    @patch("jupyter_b2.magics.display.display")
    def test_display_buckets_empty(self, mock_display):
        display_buckets([])
        html = mock_display.call_args[0][0]
        assert "No buckets found" in html.data

    @patch("jupyter_b2.magics.display.display")
    def test_display_buckets_with_data(self, mock_display):
        buckets = [
            {"name": "private-bucket", "type": "allPrivate"},
            {"name": "public-bucket", "type": "allPublic"},
        ]
        display_buckets(buckets)
        html = mock_display.call_args[0][0]
        assert "private-bucket" in html.data
        assert "public-bucket" in html.data
        assert "2 buckets" in html.data

    @patch("jupyter_b2.magics.display.display")
    def test_display_file_info(self, mock_display):
        info = {
            "fileName": "report.pdf",
            "size": 2048,
            "contentType": "application/pdf",
            "uploadTimestamp": 1704067200000,
            "fileId": "file_abc123",
            "contentSha1": "da39a3ee5e6b4b0d",
            "action": "upload",
        }
        display_file_info(info)
        html = mock_display.call_args[0][0]
        assert "report.pdf" in html.data
        assert "2.0 KB" in html.data
        assert "application/pdf" in html.data
        assert "file_abc123" in html.data

    @patch("jupyter_b2.magics.display.display")
    def test_display_auth_status_authenticated(self, mock_display):
        display_auth_status(
            authenticated=True,
            account_id="acct_123",
            api_url="https://api.backblazeb2.com",
            allowed_bucket="my-bucket",
        )
        html = mock_display.call_args[0][0]
        assert "Authenticated" in html.data
        assert "acct_123" in html.data

    @patch("jupyter_b2.magics.display.display")
    def test_display_auth_status_not_authenticated(self, mock_display):
        display_auth_status(authenticated=False)
        html = mock_display.call_args[0][0]
        assert "Not authenticated" in html.data
        assert "B2_APPLICATION_KEY_ID" in html.data

    @patch("jupyter_b2.magics.display.display")
    def test_display_upload_success(self, mock_display):
        display_upload_success("local.csv", "bucket/remote.csv", 4096, "file_xyz")
        html = mock_display.call_args[0][0]
        assert "Uploaded successfully" in html.data
        assert "local.csv" in html.data
        assert "bucket/remote.csv" in html.data

    @patch("jupyter_b2.magics.display.display")
    def test_display_download_success(self, mock_display):
        display_download_success("bucket/data.csv", "./data.csv", 8192)
        html = mock_display.call_args[0][0]
        assert "Downloaded successfully" in html.data
        assert "bucket/data.csv" in html.data
