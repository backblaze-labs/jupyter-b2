"""fsspec-compatible filesystem implementation for Backblaze B2.

This module provides ``B2FileSystem``, a read/write filesystem that integrates
with the broader Python data ecosystem through the fsspec specification.

Once registered, any library that uses ``fsspec.open()`` or ``pd.read_*("b2://...")``
will transparently work with Backblaze B2 Cloud Storage.
"""

from __future__ import annotations

import io
import os
from datetime import datetime, timezone
from typing import Any

try:
    from fsspec.spec import AbstractFileSystem

    HAS_FSSPEC = True
except ImportError:
    HAS_FSSPEC = False

    class AbstractFileSystem:  # type: ignore[no-redef]
        """Placeholder when fsspec is not installed."""

        protocol = "b2"


from b2sdk.v3 import B2Api, InMemoryAccountInfo


class B2FileSystem(AbstractFileSystem):
    """fsspec filesystem for Backblaze B2 Cloud Storage.

    Enables ``b2://bucket/path/to/file`` URIs across the Python ecosystem.

    Parameters
    ----------
        key_id: B2 application key ID. Defaults to ``B2_APPLICATION_KEY_ID`` env var.
        app_key: B2 application key. Defaults to ``B2_APPLICATION_KEY`` env var.

    Examples
    --------
        # Direct usage
        fs = B2FileSystem(key_id="...", app_key="...")
        fs.ls("my-bucket/")

        # Via pandas (after installing jupyter-b2[fsspec])
        import pandas as pd
        df = pd.read_csv("b2://my-bucket/data.csv")
    """

    protocol = "b2"

    def __init__(
        self,
        key_id: str | None = None,
        app_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the B2 filesystem."""
        if not HAS_FSSPEC:
            raise ImportError(
                "fsspec is required for B2FileSystem. "
                "Install with: pip install 'jupyter-b2[fsspec]'"
            )
        super().__init__(**kwargs)

        resolved_key_id = key_id or os.environ.get("B2_APPLICATION_KEY_ID", "")
        resolved_app_key = app_key or os.environ.get("B2_APPLICATION_KEY", "")

        if not resolved_key_id or not resolved_app_key:
            raise ValueError(
                "B2 credentials required. Provide key_id/app_key or set "
                "B2_APPLICATION_KEY_ID and B2_APPLICATION_KEY environment variables."
            )

        info = InMemoryAccountInfo()
        self._api = B2Api(info)
        self._api.authorize_account("production", resolved_key_id, resolved_app_key)
        self._bucket_cache: dict[str, Any] = {}

    def _get_bucket(self, bucket_name: str) -> Any:
        """Get bucket by name with caching."""
        if bucket_name not in self._bucket_cache:
            self._bucket_cache[bucket_name] = self._api.get_bucket_by_name(bucket_name)
        return self._bucket_cache[bucket_name]

    @staticmethod
    def _split_path(path: str) -> tuple[str, str]:
        """Split a b2 path into (bucket, key)."""
        path = path.lstrip("/")
        if "/" in path:
            bucket, key = path.split("/", 1)
            return bucket, key.rstrip("/")
        return path, ""

    def ls(self, path: str, detail: bool = False, **kwargs: Any) -> list[Any]:
        """List objects under a path.

        Parameters
        ----------
            path: B2 path (e.g., "my-bucket/prefix/").
            detail: If True, return dicts with full metadata.
            **kwargs: Additional arguments (ignored).

        Returns
        -------
            List of paths (str) or metadata dicts.
        """
        bucket_name, prefix = self._split_path(path)

        if not bucket_name:
            buckets = self._api.list_buckets()
            if detail:
                return [{"name": b.name, "type": "directory", "size": 0} for b in buckets]
            return [b.name for b in buckets]

        bucket = self._get_bucket(bucket_name)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        results = []
        for file_version, _folder_name in bucket.ls(path=prefix, latest_only=True, recursive=False):
            full_path = f"{bucket_name}/{file_version.file_name}"
            if detail:
                results.append(
                    {
                        "name": full_path,
                        "size": file_version.size or 0,
                        "type": "directory" if file_version.file_name.endswith("/") else "file",
                        "last_modified": datetime.fromtimestamp(
                            (file_version.upload_timestamp or 0) / 1000, tz=timezone.utc
                        ),
                    }
                )
            else:
                results.append(full_path)

        return results

    def info(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Get metadata for a single file."""
        bucket_name, key = self._split_path(path)
        if not key:
            return {"name": path, "type": "directory", "size": 0}

        bucket = self._get_bucket(bucket_name)
        file_version = bucket.get_file_info_by_name(key)

        return {
            "name": path,
            "size": file_version.size or 0,
            "type": "file",
            "last_modified": datetime.fromtimestamp(
                (file_version.upload_timestamp or 0) / 1000, tz=timezone.utc
            ),
            "content_type": file_version.content_type,
            "file_id": file_version.id_,
        }

    def _open(
        self,
        path: str,
        mode: str = "rb",
        **kwargs: Any,
    ) -> io.BytesIO:
        """Open a file for reading or writing.

        Parameters
        ----------
            path: B2 path.
            mode: File mode ("rb" for read, "wb" for write).
            **kwargs: Additional arguments (ignored).

        Returns
        -------
            BytesIO buffer.
        """
        bucket_name, key = self._split_path(path)
        bucket = self._get_bucket(bucket_name)

        if "r" in mode:
            downloaded = bucket.download_file_by_name(key)
            buffer = io.BytesIO()
            downloaded.save(buffer)
            buffer.seek(0)
            return buffer
        elif "w" in mode:
            return _B2WriteBuffer(bucket, key)
        else:
            raise ValueError(f"Unsupported mode: {mode}")

    def cat_file(
        self,
        path: str,
        start: int | None = None,
        end: int | None = None,
        **kwargs: Any,
    ) -> bytes:
        """Read a file's contents as bytes."""
        bucket_name, key = self._split_path(path)
        bucket = self._get_bucket(bucket_name)

        range_ = None
        if start is not None or end is not None:
            range_ = (start or 0, end or 0)

        downloaded = bucket.download_file_by_name(key, range_=range_)
        buffer = io.BytesIO()
        downloaded.save(buffer)
        return buffer.getvalue()

    def put_file(self, lpath: str, rpath: str, **kwargs: Any) -> None:
        """Upload a local file to B2."""
        bucket_name, key = self._split_path(rpath)
        bucket = self._get_bucket(bucket_name)
        bucket.upload_local_file(lpath, key)

    def rm_file(self, path: str) -> None:
        """Delete a file from B2."""
        bucket_name, key = self._split_path(path)
        bucket = self._get_bucket(bucket_name)
        file_version = bucket.get_file_info_by_name(key)
        self._api.delete_file_version(file_version.id_, file_version.file_name)

    def exists(self, path: str, **kwargs: Any) -> bool:
        """Check if a path exists."""
        try:
            self.info(path)
            return True
        except Exception:
            return False

    def created(self, path: str) -> datetime | None:
        """Get creation time (same as modified for B2)."""
        return self.modified(path)

    def modified(self, path: str) -> datetime | None:
        """Get last modified time."""
        info = self.info(path)
        return info.get("last_modified")


class _B2WriteBuffer(io.BytesIO):
    """A write buffer that uploads to B2 on close."""

    def __init__(self, bucket: Any, key: str) -> None:
        super().__init__()
        self._bucket = bucket
        self._key = key

    def close(self) -> None:
        """Upload the buffer contents to B2 and close."""
        if not self.closed:
            self.seek(0)
            self._bucket.upload_bytes(self.read(), self._key)
        super().close()
