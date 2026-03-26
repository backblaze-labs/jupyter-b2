"""Data loading utilities — smart format detection and DataFrame integration."""

from __future__ import annotations

import io
import json
from pathlib import PurePosixPath
from typing import Any, Optional

from b2sdk.v3 import B2Api


# Supported formats and their pandas read functions
_PANDAS_READERS: dict[str, str] = {
    ".csv": "read_csv",
    ".tsv": "read_csv",
    ".parquet": "read_parquet",
    ".json": "read_json",
    ".jsonl": "read_json",
    ".feather": "read_feather",
    ".orc": "read_orc",
    ".xlsx": "read_excel",
    ".xls": "read_excel",
}

_POLARS_READERS: dict[str, str] = {
    ".csv": "read_csv",
    ".tsv": "read_csv",
    ".parquet": "read_parquet",
    ".json": "read_json",
    ".jsonl": "read_ndjson",
    ".feather": "read_ipc",
    ".avro": "read_avro",
}


def _parse_b2_path(path: str) -> tuple[str, str]:
    """Parse a b2:// path or bucket/key path into (bucket, key).

    Supports:
        - ``b2://bucket/path/to/file.csv``
        - ``bucket/path/to/file.csv``

    Returns:
        Tuple of (bucket_name, file_key).
    """
    if path.startswith("b2://"):
        path = path[5:]
    parts = path.split("/", 1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def _detect_format(file_key: str) -> str:
    """Detect file format from extension."""
    return PurePosixPath(file_key).suffix.lower()


def download_to_buffer(api: B2Api, bucket_name: str, file_key: str) -> io.BytesIO:
    """Download a B2 file into an in-memory buffer.

    Args:
        api: Authenticated B2Api instance.
        bucket_name: Name of the bucket.
        file_key: File key/path within the bucket.

    Returns:
        BytesIO buffer containing the file data.
    """
    bucket = api.get_bucket_by_name(bucket_name)
    downloaded = bucket.download_file_by_name(file_key)
    buffer = io.BytesIO()
    downloaded.save(buffer)
    buffer.seek(0)
    return buffer


def load_as_pandas(
    api: B2Api,
    bucket_name: str,
    file_key: str,
    *,
    format_hint: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """Load a B2 file directly into a pandas DataFrame.

    Args:
        api: Authenticated B2Api instance.
        bucket_name: Bucket name.
        file_key: File path in the bucket.
        format_hint: Override auto-detected format (e.g., ".csv", ".parquet").
        **kwargs: Additional arguments passed to the pandas read function.

    Returns:
        pandas DataFrame.

    Raises:
        ImportError: If pandas is not installed.
        ValueError: If the file format is not supported.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(
            "pandas is required for %b2_load --as df. "
            "Install with: pip install 'b2-jupyter[pandas]'"
        )

    ext = format_hint or _detect_format(file_key)
    reader_name = _PANDAS_READERS.get(ext)
    if reader_name is None:
        raise ValueError(
            f"Unsupported format '{ext}' for pandas. "
            f"Supported: {', '.join(_PANDAS_READERS.keys())}"
        )

    buffer = download_to_buffer(api, bucket_name, file_key)

    reader_fn = getattr(pd, reader_name)
    # Special handling for TSV
    if ext == ".tsv" and "sep" not in kwargs:
        kwargs["sep"] = "\t"
    # Special handling for JSONL
    if ext == ".jsonl" and "lines" not in kwargs:
        kwargs["lines"] = True

    return reader_fn(buffer, **kwargs)


def load_as_polars(
    api: B2Api,
    bucket_name: str,
    file_key: str,
    *,
    format_hint: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """Load a B2 file directly into a Polars DataFrame.

    Args:
        api: Authenticated B2Api instance.
        bucket_name: Bucket name.
        file_key: File path in the bucket.
        format_hint: Override auto-detected format.
        **kwargs: Additional arguments passed to the Polars read function.

    Returns:
        polars DataFrame.
    """
    try:
        import polars as pl
    except ImportError:
        raise ImportError(
            "polars is required for %b2_load --as polars. "
            "Install with: pip install polars"
        )

    ext = format_hint or _detect_format(file_key)
    reader_name = _POLARS_READERS.get(ext)
    if reader_name is None:
        raise ValueError(
            f"Unsupported format '{ext}' for polars. "
            f"Supported: {', '.join(_POLARS_READERS.keys())}"
        )

    buffer = download_to_buffer(api, bucket_name, file_key)

    reader_fn = getattr(pl, reader_name)
    if ext == ".tsv" and "separator" not in kwargs:
        kwargs["separator"] = "\t"

    return reader_fn(buffer, **kwargs)


def load_as_bytes(api: B2Api, bucket_name: str, file_key: str) -> bytes:
    """Load a B2 file as raw bytes."""
    buffer = download_to_buffer(api, bucket_name, file_key)
    return buffer.read()


def load_as_text(
    api: B2Api, bucket_name: str, file_key: str, encoding: str = "utf-8"
) -> str:
    """Load a B2 file as a text string."""
    raw = load_as_bytes(api, bucket_name, file_key)
    return raw.decode(encoding)


def load_as_json(api: B2Api, bucket_name: str, file_key: str) -> Any:
    """Load a B2 JSON file as a Python object."""
    text = load_as_text(api, bucket_name, file_key)
    return json.loads(text)
