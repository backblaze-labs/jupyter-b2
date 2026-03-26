"""Authentication management for B2 magic commands."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from b2sdk.v3 import B2Api, InMemoryAccountInfo, SqliteAccountInfo


@dataclass
class B2AuthManager:
    """Manage B2 authentication state across magic command invocations.

    Supports three authentication strategies (in priority order):
    1. Explicit: ``%b2 auth --key-id <id> --key <key>``
    2. Environment variables: ``B2_APPLICATION_KEY_ID`` + ``B2_APPLICATION_KEY``
    3. Stored credentials: Piggyback on B2 CLI's ``~/.b2_account_info``
    """

    _api: B2Api | None = field(default=None, init=False, repr=False)
    _key_id: str | None = field(default=None, init=False, repr=False)
    _app_key: str | None = field(default=None, init=False, repr=False)

    @property
    def api(self) -> B2Api:
        """Get the authenticated B2Api instance, auto-authorizing if possible."""
        if self._api is not None:
            return self._api
        return self._auto_authorize()

    @property
    def is_authenticated(self) -> bool:
        """Check if we have an active authenticated session."""
        return self._api is not None

    def authorize(
        self,
        key_id: str | None = None,
        app_key: str | None = None,
        *,
        realm: str = "production",
    ) -> B2Api:
        """Explicitly authorize with B2 credentials.

        Parameters
        ----------
            key_id: B2 application key ID. Falls back to ``B2_APPLICATION_KEY_ID`` env var.
            app_key: B2 application key. Falls back to ``B2_APPLICATION_KEY`` env var.
            realm: B2 realm (default: "production").

        Returns
        -------
            Authenticated B2Api instance.

        Raises
        ------
            ValueError: If no credentials are provided or found.
        """
        resolved_key_id = key_id or os.environ.get("B2_APPLICATION_KEY_ID")
        resolved_app_key = app_key or os.environ.get("B2_APPLICATION_KEY")

        if resolved_key_id and resolved_app_key:
            return self._authorize_with_keys(resolved_key_id, resolved_app_key, realm)

        return self._authorize_from_stored()

    def deauthorize(self) -> None:
        """Clear the current authentication session."""
        self._api = None
        self._key_id = None
        self._app_key = None

    def _auto_authorize(self) -> B2Api:
        """Attempt automatic authorization from env vars or stored credentials."""
        key_id = os.environ.get("B2_APPLICATION_KEY_ID")
        app_key = os.environ.get("B2_APPLICATION_KEY")

        if key_id and app_key:
            return self._authorize_with_keys(key_id, app_key)

        return self._authorize_from_stored()

    def _authorize_with_keys(self, key_id: str, app_key: str, realm: str = "production") -> B2Api:
        """Authorize using explicit key ID and application key."""
        info = InMemoryAccountInfo()
        api = B2Api(info)
        api.authorize_account(key_id, app_key, realm=realm)
        self._api = api
        self._key_id = key_id
        self._app_key = app_key
        return api

    def _authorize_from_stored(self) -> B2Api:
        """Authorize using stored credentials from B2 CLI.

        Uses the SDK's ``SqliteAccountInfo`` which automatically resolves
        the credential file path in this order:

        1. ``~/.b2_account_info`` (legacy default)
        2. ``$XDG_CONFIG_HOME/b2/account_info`` (Linux/BSD XDG)
        3. Profile-specific DB files (``b2 authorize-account --profile <name>``)

        This means if you've ever run ``b2 authorize-account`` (or
        ``b2 account authorize``), the magic commands will auto-authenticate.
        """
        try:
            info = SqliteAccountInfo()
            api = B2Api(info)
            # Verify the stored credentials are still valid by checking
            # that we have an account ID (set during authorize_account)
            if not info.get_account_id():
                raise ValueError("Stored credentials are empty")
            self._api = api
            return api
        except Exception as err:
            raise ValueError(
                "No B2 credentials found. Authenticate using one of:\n"
                "  1. %b2 auth --key-id <id> --key <key>\n"
                "  2. Set B2_APPLICATION_KEY_ID and B2_APPLICATION_KEY env vars\n"
                "  3. Run 'b2 authorize-account <key-id> <app-key>' in terminal\n"
                "  4. Install B2 CLI: pip install b2"
            ) from err

    def get_s3_credentials(self) -> dict[str, str]:
        """Get S3-compatible credentials for use with boto3/fsspec.

        Returns
        -------
            Dict with ``endpoint_url``, ``aws_access_key_id``, ``aws_secret_access_key``.
        """
        api = self.api
        account_info = api.account_info
        return {
            "endpoint_url": account_info.get_s3_api_url(),
            "aws_access_key_id": self._key_id or account_info.get_account_id(),
            "aws_secret_access_key": self._app_key or "",
        }
