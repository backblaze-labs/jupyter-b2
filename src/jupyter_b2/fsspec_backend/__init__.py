"""fsspec filesystem implementation for Backblaze B2.

Registers the ``b2://`` protocol with fsspec, enabling native integration
with pandas, polars, dask, xarray, HuggingFace datasets, and any other
library that uses fsspec for filesystem abstraction.

Usage::

    import jupyter_b2  # registers b2:// protocol

    import pandas as pd
    df = pd.read_csv("b2://my-bucket/data/train.csv")
    df.to_parquet("b2://my-bucket/data/train.parquet")

    import polars as pl
    df = pl.read_parquet("b2://my-bucket/data/train.parquet")

Configuration via environment variables::

    B2_APPLICATION_KEY_ID=<key_id>
    B2_APPLICATION_KEY=<key>
"""

from __future__ import annotations

from jupyter_b2.fsspec_backend.filesystem import B2FileSystem

__all__ = ["B2FileSystem"]
