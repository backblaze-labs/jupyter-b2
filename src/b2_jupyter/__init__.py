"""b2-jupyter: Jupyter/IPython magic commands and fsspec backend for Backblaze B2."""

from __future__ import annotations

__version__ = "0.1.0"


def load_ipython_extension(ipython):
    """Load the b2-jupyter IPython extension.

    Usage in a notebook::

        %load_ext b2_jupyter

    This registers all B2 magic commands:
        - %b2 auth       — Authenticate with B2
        - %b2 ls         — List bucket contents
        - %b2 info       — File metadata and versions
        - %b2 upload     — Upload local file to B2
        - %b2 download   — Download file from B2
        - %b2 cp         — Copy between B2 paths
        - %b2 rm         — Delete a file
        - %b2 presign    — Generate pre-signed URL
        - %b2 buckets    — List all buckets
        - %b2_load       — Load file into a variable (DataFrame, bytes, text)
        - %%b2_save      — Save cell output / variable to B2
    """
    from b2_jupyter.magics import B2Magics

    ipython.register_magics(B2Magics)


def unload_ipython_extension(ipython):
    """Unload the b2-jupyter IPython extension."""
