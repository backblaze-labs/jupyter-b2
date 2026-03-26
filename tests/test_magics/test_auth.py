"""Tests for the B2 authentication manager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from jupyter_b2.magics.auth import B2AuthManager


class TestB2AuthManager:
    """Tests for B2AuthManager."""

    def test_initial_state(self):
        auth = B2AuthManager()
        assert not auth.is_authenticated
        assert auth._api is None

    def test_authorize_with_explicit_keys(self):
        auth = B2AuthManager()
        with patch("jupyter_b2.magics.auth.B2Api") as mock_api_cls:
            mock_api = MagicMock()
            mock_api_cls.return_value = mock_api

            result = auth.authorize(key_id="test-id", app_key="test-key")

            mock_api.authorize_account.assert_called_once_with(
                "test-id", "test-key", realm="production"
            )
            assert auth.is_authenticated
            assert result is mock_api

    def test_authorize_with_env_vars(self, monkeypatch):
        monkeypatch.setenv("B2_APPLICATION_KEY_ID", "env-id")
        monkeypatch.setenv("B2_APPLICATION_KEY", "env-key")

        auth = B2AuthManager()
        with patch("jupyter_b2.magics.auth.B2Api") as mock_api_cls:
            mock_api = MagicMock()
            mock_api_cls.return_value = mock_api

            auth.authorize()

            mock_api.authorize_account.assert_called_once_with(
                "env-id", "env-key", realm="production"
            )
            assert auth.is_authenticated

    def test_authorize_falls_back_to_stored(self, monkeypatch):
        monkeypatch.delenv("B2_APPLICATION_KEY_ID", raising=False)
        monkeypatch.delenv("B2_APPLICATION_KEY", raising=False)

        mock_info = MagicMock()
        mock_info.get_account_id.return_value = "stored-account-id"

        with (
            patch("jupyter_b2.magics.auth.SqliteAccountInfo", return_value=mock_info),
            patch("jupyter_b2.magics.auth.B2Api") as mock_api_cls,
        ):
            mock_api = MagicMock()
            mock_api_cls.return_value = mock_api

            auth = B2AuthManager()
            result = auth.authorize()
            assert result is mock_api

    def test_authorize_no_credentials_raises(self, monkeypatch):
        monkeypatch.delenv("B2_APPLICATION_KEY_ID", raising=False)
        monkeypatch.delenv("B2_APPLICATION_KEY", raising=False)

        # Mock SqliteAccountInfo to raise (no stored credentials)
        with patch(
            "jupyter_b2.magics.auth.SqliteAccountInfo",
            side_effect=Exception("No credentials file"),
        ):
            auth = B2AuthManager()
            with pytest.raises(ValueError, match="No B2 credentials found"):
                auth.authorize()

    def test_deauthorize(self):
        auth = B2AuthManager()
        with patch("jupyter_b2.magics.auth.B2Api") as mock_api_cls:
            mock_api = MagicMock()
            mock_api_cls.return_value = mock_api
            auth.authorize(key_id="test-id", app_key="test-key")

            assert auth.is_authenticated
            auth.deauthorize()
            assert not auth.is_authenticated

    def test_api_property_auto_authorizes_from_env(self, monkeypatch):
        monkeypatch.setenv("B2_APPLICATION_KEY_ID", "auto-id")
        monkeypatch.setenv("B2_APPLICATION_KEY", "auto-key")

        with patch("jupyter_b2.magics.auth.B2Api") as mock_api_cls:
            mock_api = MagicMock()
            mock_api_cls.return_value = mock_api

            auth = B2AuthManager()
            result = auth.api

            mock_api.authorize_account.assert_called_once_with(
                "auto-id", "auto-key", realm="production"
            )
            assert result is mock_api

    def test_api_property_raises_without_credentials(self, monkeypatch):
        monkeypatch.delenv("B2_APPLICATION_KEY_ID", raising=False)
        monkeypatch.delenv("B2_APPLICATION_KEY", raising=False)

        # Mock SqliteAccountInfo to raise (no stored credentials)
        with patch(
            "jupyter_b2.magics.auth.SqliteAccountInfo",
            side_effect=Exception("No credentials file"),
        ):
            auth = B2AuthManager()
            with pytest.raises(ValueError, match="No B2 credentials found"):
                _ = auth.api

    def test_get_s3_credentials(self, monkeypatch):
        auth = B2AuthManager()
        with patch("jupyter_b2.magics.auth.B2Api") as mock_api_cls:
            mock_api = MagicMock()
            mock_api.account_info.get_s3_api_url.return_value = (
                "https://s3.us-west-004.backblazeb2.com"
            )
            mock_api.account_info.get_account_id.return_value = "acct_123"
            mock_api_cls.return_value = mock_api

            auth.authorize(key_id="my-key-id", app_key="my-app-key")
            creds = auth.get_s3_credentials()

            assert creds["endpoint_url"] == "https://s3.us-west-004.backblazeb2.com"
            assert creds["aws_access_key_id"] == "my-key-id"
            assert creds["aws_secret_access_key"] == "my-app-key"
