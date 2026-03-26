"""jupyter-b2: Jupyter/IPython magic commands and fsspec backend for Backblaze B2."""

from __future__ import annotations

from typing import Any

__version__ = "0.1.0"


def load_ipython_extension(ipython: Any) -> None:
    """Load the jupyter-b2 IPython extension.

    Usage in a notebook::

        %load_ext jupyter_b2

    On load, automatically attempts to authenticate using (in order):

    1. Environment variables: ``B2_APPLICATION_KEY_ID`` + ``B2_APPLICATION_KEY``
    2. B2 CLI stored credentials (from ``b2 authorize-account``)

    If auto-auth succeeds, you can immediately use all commands.
    If not, use ``%b2 auth`` to authenticate interactively.

    Available magic commands:

        - ``%b2 auth``       — Authenticate with B2
        - ``%b2 buckets``    — List all buckets
        - ``%b2 ls``         — List bucket contents
        - ``%b2 info``       — File metadata and versions
        - ``%b2 upload``     — Upload local file to B2
        - ``%b2 download``   — Download file from B2
        - ``%b2 cp``         — Copy between B2 paths
        - ``%b2 rm``         — Delete a file
        - ``%b2 presign``    — Generate pre-signed URL
        - ``%b2_load``       — Load file into a variable (DataFrame, bytes, text)
        - ``%%b2_save``      — Save cell output / variable to B2
    """
    from jupyter_b2.magics import B2Magics

    magics = B2Magics(ipython)
    ipython.register_magics(magics)

    # Attempt auto-authentication silently
    try:
        api = magics._auth.api
        account_id = api.account_info.get_account_id()
        api_url = api.account_info.get_api_url()
        from jupyter_b2.magics.display import display_auth_status

        display_auth_status(
            authenticated=True,
            account_id=account_id,
            api_url=api_url,
        )
    except Exception:
        # Auto-auth failed — that's fine, user can run %b2 auth later
        from IPython.display import HTML, display

        display(
            HTML(
                '<div style="border: 1px solid #ff9800; border-radius: 8px; '
                "padding: 12px; margin: 8px 0; background: #fff8e1; "
                'font-size: 13px;">'
                "<strong>B2 Magic Commands loaded</strong> — "
                "not authenticated yet.<br>"
                "Run <code>%b2 auth</code> or set "
                "<code>B2_APPLICATION_KEY_ID</code> / "
                "<code>B2_APPLICATION_KEY</code> env vars.<br>"
                "Tip: run <code>pip install b2 && b2 account authorize</code> "
                "for persistent auth."
                "</div>"
            )
        )


def unload_ipython_extension(ipython: Any) -> None:
    """Unload the jupyter-b2 IPython extension."""
