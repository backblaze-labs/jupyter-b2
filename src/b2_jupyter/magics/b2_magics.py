"""Core B2 IPython magic commands.

Usage::

    %load_ext b2_jupyter

    # Authenticate
    %b2 auth --key-id <id> --key <key>

    # List buckets
    %b2 buckets

    # List files
    %b2 ls my-bucket/path/to/dir/

    # File info
    %b2 info my-bucket/path/to/file.csv

    # Upload / Download
    %b2 upload local_file.csv my-bucket/data/file.csv
    %b2 download my-bucket/data/file.csv ./local_file.csv

    # Load directly into DataFrame
    df = %b2_load my-bucket/data/train.csv
    df = %b2_load my-bucket/data/train.parquet --as polars

    # Save variable to B2
    %%b2_save my-bucket/results/output.parquet
    df

    # Generate pre-signed URL
    %b2 presign my-bucket/data/file.csv --expires 3600

    # Delete
    %b2 rm my-bucket/path/to/file.csv
"""

from __future__ import annotations

import io
import shlex
import sys
from getpass import getpass
from pathlib import Path
from typing import Any, Optional

from IPython.core.magic import Magics, cell_magic, line_magic, magics_class
from IPython.display import display

from b2_jupyter.magics.auth import B2AuthManager
from b2_jupyter.magics.display import (
    display_auth_status,
    display_buckets,
    display_download_success,
    display_file_info,
    display_file_list,
    display_upload_success,
)
from b2_jupyter.magics.loaders import (
    _parse_b2_path,
    load_as_bytes,
    load_as_json,
    load_as_pandas,
    load_as_polars,
    load_as_text,
)


def _parse_args(line: str) -> list[str]:
    """Safely parse a magic command line into arguments."""
    try:
        return shlex.split(line)
    except ValueError:
        return line.split()


@magics_class
class B2Magics(Magics):
    """IPython magic commands for Backblaze B2 Cloud Storage.

    Provides ``%b2`` (line magic), ``%b2_load`` (line magic), and
    ``%%b2_save`` (cell magic) for interacting with B2 from Jupyter notebooks.
    """

    def __init__(self, shell: Any) -> None:
        """Initialize with an IPython shell instance."""
        super().__init__(shell)
        self._auth = B2AuthManager()

    # ─── Main dispatcher ───────────────────────────────────────────────

    @line_magic
    def b2(self, line: str) -> Optional[Any]:
        """Dispatch B2 sub-commands.

        Usage: ``%b2 <subcommand> [args...]``
        """
        args = _parse_args(line)
        if not args:
            return self._print_help()

        subcommand = args[0]
        rest = " ".join(args[1:])

        dispatch = {
            "auth": self._cmd_auth,
            "buckets": self._cmd_buckets,
            "ls": self._cmd_ls,
            "info": self._cmd_info,
            "upload": self._cmd_upload,
            "download": self._cmd_download,
            "cp": self._cmd_cp,
            "rm": self._cmd_rm,
            "presign": self._cmd_presign,
            "status": self._cmd_status,
            "help": self._print_help,
        }

        handler = dispatch.get(subcommand)
        if handler is None:
            print(f"Unknown subcommand: {subcommand}. Use '%b2 help' for usage.", file=sys.stderr)
            return None

        return handler(rest) if subcommand != "help" else handler()

    # ─── %b2_load — Load file into variable ────────────────────────────

    @line_magic
    def b2_load(self, line: str) -> Any:
        """Load a B2 file directly into a Python variable.

        Usage::

            df = %b2_load my-bucket/data/train.csv
            df = %b2_load b2://my-bucket/data/train.parquet --as polars
            text = %b2_load my-bucket/config.yaml --as text
            data = %b2_load my-bucket/model.bin --as bytes
            obj = %b2_load my-bucket/data.json --as json

        Supported ``--as`` targets:
            - ``df`` / ``pandas`` (default for tabular formats)
            - ``polars``
            - ``text``
            - ``bytes``
            - ``json``

        Auto-detects format from file extension (.csv, .parquet, .json, .tsv, etc.)
        """
        args = _parse_args(line)
        if not args:
            print("Usage: %b2_load <bucket/path> [--as df|polars|text|bytes|json]", file=sys.stderr)
            return None

        path = args[0]
        target = "df"  # default

        if "--as" in args:
            idx = args.index("--as")
            if idx + 1 < len(args):
                target = args[idx + 1]

        bucket_name, file_key = _parse_b2_path(path)
        if not file_key:
            print("Error: Please provide a file path, not just a bucket name.", file=sys.stderr)
            return None

        api = self._auth.api
        print(f"Loading b2://{bucket_name}/{file_key} ...", end=" ", flush=True)

        if target in ("df", "pandas"):
            result = load_as_pandas(api, bucket_name, file_key)
            print(f"✅ DataFrame ({result.shape[0]} rows, {result.shape[1]} cols)")
            return result
        elif target == "polars":
            result = load_as_polars(api, bucket_name, file_key)
            print(f"✅ Polars DataFrame ({result.shape[0]} rows, {result.shape[1]} cols)")
            return result
        elif target == "text":
            result = load_as_text(api, bucket_name, file_key)
            print(f"✅ Text ({len(result)} chars)")
            return result
        elif target == "bytes":
            result = load_as_bytes(api, bucket_name, file_key)
            print(f"✅ Bytes ({len(result)} bytes)")
            return result
        elif target == "json":
            result = load_as_json(api, bucket_name, file_key)
            print("✅ JSON loaded")
            return result
        else:
            print(f"Error: Unknown target '{target}'. Use df, polars, text, bytes, or json.")
            return None

    # ─── %%b2_save — Save variable to B2 ───────────────────────────────

    @cell_magic
    def b2_save(self, line: str, cell: str) -> None:
        """Save a variable or cell output to B2.

        Usage::

            %%b2_save my-bucket/results/output.csv
            df

            %%b2_save my-bucket/results/output.parquet
            df

            %%b2_save my-bucket/config/settings.json
            {"key": "value", "nested": [1, 2, 3]}
        """
        args = _parse_args(line)
        if not args:
            print("Usage: %%b2_save <bucket/path>", file=sys.stderr)
            return

        path = args[0]
        bucket_name, file_key = _parse_b2_path(path)
        if not file_key:
            print("Error: Please provide a full file path.", file=sys.stderr)
            return

        # Evaluate the cell to get the variable
        cell = cell.strip()
        try:
            obj = self.shell.ev(cell)  # type: ignore[union-attr]
        except Exception:
            # If eval fails, treat cell content as raw text
            obj = cell

        # Serialize based on extension and object type
        data = self._serialize_for_upload(obj, file_key)

        api = self._auth.api
        bucket = api.get_bucket_by_name(bucket_name)

        print(f"Saving to b2://{bucket_name}/{file_key} ...", end=" ", flush=True)
        file_version = bucket.upload_bytes(data, file_key)
        print("✅")
        display_upload_success("(in-memory)", f"{bucket_name}/{file_key}", len(data), file_version.id_)

    # ─── Sub-command implementations ───────────────────────────────────

    def _cmd_auth(self, line: str) -> None:
        """Authenticate with B2."""
        args = _parse_args(line)

        key_id = None
        app_key = None

        if "--key-id" in args:
            idx = args.index("--key-id")
            if idx + 1 < len(args):
                key_id = args[idx + 1]

        if "--key" in args:
            idx = args.index("--key")
            if idx + 1 < len(args):
                app_key = args[idx + 1]

        # Interactive mode if no key provided
        if not key_id and not app_key:
            import os

            key_id = os.environ.get("B2_APPLICATION_KEY_ID")
            app_key = os.environ.get("B2_APPLICATION_KEY")

            if not key_id:
                key_id = input("B2 Application Key ID: ").strip()
            if not app_key:
                app_key = getpass("B2 Application Key: ").strip()

        try:
            api = self._auth.authorize(key_id=key_id, app_key=app_key)
            info = api.account_info
            display_auth_status(
                authenticated=True,
                account_id=info.get_account_id(),
                api_url=info.get_api_url(),
                allowed_bucket=getattr(info, "get_allowed_bucket_name", lambda: "")()
                if hasattr(info, "get_allowed_bucket_name")
                else "",
            )
        except Exception as e:
            print(f"Authentication failed: {e}", file=sys.stderr)

    def _cmd_status(self, line: str) -> None:
        """Show authentication status."""
        if self._auth.is_authenticated:
            info = self._auth.api.account_info
            display_auth_status(
                authenticated=True,
                account_id=info.get_account_id(),
                api_url=info.get_api_url(),
            )
        else:
            display_auth_status(authenticated=False)

    def _cmd_buckets(self, line: str) -> None:
        """List all buckets."""
        api = self._auth.api
        buckets = api.list_buckets()
        display_buckets([{"name": b.name, "type": b.type_} for b in buckets])

    def _cmd_ls(self, line: str) -> None:
        """List files in a bucket/prefix."""
        args = _parse_args(line)
        if not args:
            print("Usage: %b2 ls <bucket>[/prefix] [--recursive]", file=sys.stderr)
            return

        recursive = "--recursive" in args or "-r" in args
        path = args[0]
        bucket_name, prefix = _parse_b2_path(path)

        api = self._auth.api
        bucket = api.get_bucket_by_name(bucket_name)

        files = []
        for file_version, _folder in bucket.ls(
            folder_to_list=prefix,
            latest_only=True,
            recursive=recursive,
        ):
            files.append({
                "name": file_version.file_name,
                "size": file_version.size,
                "uploadTimestamp": file_version.upload_timestamp,
                "fileId": file_version.id_,
                "contentType": file_version.content_type,
            })

        display_file_list(files, bucket_name, prefix)

    def _cmd_info(self, line: str) -> None:
        """Show file metadata."""
        args = _parse_args(line)
        if not args:
            print("Usage: %b2 info <bucket/path>", file=sys.stderr)
            return

        bucket_name, file_key = _parse_b2_path(args[0])
        api = self._auth.api
        bucket = api.get_bucket_by_name(bucket_name)
        file_version = bucket.get_file_info_by_name(file_key)

        display_file_info({
            "fileName": file_version.file_name,
            "size": file_version.size,
            "contentType": file_version.content_type,
            "uploadTimestamp": file_version.upload_timestamp,
            "fileId": file_version.id_,
            "contentSha1": file_version.content_sha1,
            "action": file_version.action,
        })

    def _cmd_upload(self, line: str) -> None:
        """Upload a local file to B2."""
        args = _parse_args(line)
        if len(args) < 2:
            print("Usage: %b2 upload <local_path> <bucket/remote_path>", file=sys.stderr)
            return

        local_path = Path(args[0]).expanduser()
        if not local_path.exists():
            print(f"Error: Local file not found: {local_path}", file=sys.stderr)
            return

        bucket_name, file_key = _parse_b2_path(args[1])
        if not file_key:
            file_key = local_path.name

        api = self._auth.api
        bucket = api.get_bucket_by_name(bucket_name)

        print(f"Uploading {local_path} → b2://{bucket_name}/{file_key} ...", flush=True)
        file_version = bucket.upload_local_file(str(local_path), file_key)
        display_upload_success(
            str(local_path),
            f"{bucket_name}/{file_key}",
            local_path.stat().st_size,
            file_version.id_,
        )

    def _cmd_download(self, line: str) -> None:
        """Download a file from B2."""
        args = _parse_args(line)
        if not args:
            print("Usage: %b2 download <bucket/path> [local_path]", file=sys.stderr)
            return

        bucket_name, file_key = _parse_b2_path(args[0])
        local_path = Path(args[1]) if len(args) > 1 else Path(file_key.split("/")[-1])

        api = self._auth.api
        bucket = api.get_bucket_by_name(bucket_name)

        print(f"Downloading b2://{bucket_name}/{file_key} ...", flush=True)
        downloaded = bucket.download_file_by_name(file_key)
        downloaded.save_to(str(local_path))

        display_download_success(
            f"{bucket_name}/{file_key}",
            str(local_path),
            local_path.stat().st_size,
        )

    def _cmd_cp(self, line: str) -> None:
        """Copy a file within B2."""
        args = _parse_args(line)
        if len(args) < 2:
            print("Usage: %b2 cp <bucket/source> <bucket/dest>", file=sys.stderr)
            return

        src_bucket, src_key = _parse_b2_path(args[0])
        dst_bucket, dst_key = _parse_b2_path(args[1])

        api = self._auth.api
        source_bucket = api.get_bucket_by_name(src_bucket)
        source_file = source_bucket.get_file_info_by_name(src_key)

        dest_bucket = api.get_bucket_by_name(dst_bucket)
        print(f"Copying b2://{src_bucket}/{src_key} → b2://{dst_bucket}/{dst_key} ...", end=" ")
        dest_bucket.copy(source_file.id_, dst_key)
        print("✅")

    def _cmd_rm(self, line: str) -> None:
        """Delete a file from B2."""
        args = _parse_args(line)
        if not args:
            print("Usage: %b2 rm <bucket/path>", file=sys.stderr)
            return

        bucket_name, file_key = _parse_b2_path(args[0])
        api = self._auth.api
        bucket = api.get_bucket_by_name(bucket_name)
        file_version = bucket.get_file_info_by_name(file_key)

        print(f"Deleting b2://{bucket_name}/{file_key} ...", end=" ")
        api.delete_file_version(file_version.id_, file_version.file_name)
        print("✅ Deleted")

    def _cmd_presign(self, line: str) -> None:
        """Generate a pre-signed download URL."""
        args = _parse_args(line)
        if not args:
            print("Usage: %b2 presign <bucket/path> [--expires SECONDS]", file=sys.stderr)
            return

        bucket_name, file_key = _parse_b2_path(args[0])
        expires = 3600  # default 1 hour

        if "--expires" in args:
            idx = args.index("--expires")
            if idx + 1 < len(args):
                expires = int(args[idx + 1])

        api = self._auth.api
        bucket = api.get_bucket_by_name(bucket_name)
        auth_token = bucket.get_download_authorization(file_key, expires)
        base_url = api.account_info.get_download_url()
        url = f"{base_url}/file/{bucket_name}/{file_key}?Authorization={auth_token}"

        from IPython.display import HTML, display

        display(HTML(
            f'<div style="margin: 8px 0; font-size: 13px;">'
            f'<strong>🔗 Pre-signed URL</strong> (expires in {expires}s)<br>'
            f'<code style="word-break: break-all;">{url}</code></div>'
        ))

    def _print_help(self) -> None:
        """Print help message."""
        help_text = """
B2 Jupyter Magic Commands
═════════════════════════

Authentication:
  %b2 auth                         Interactive authentication
  %b2 auth --key-id ID --key KEY   Authenticate with explicit credentials
  %b2 status                       Show auth status

Browsing:
  %b2 buckets                      List all buckets
  %b2 ls bucket/prefix/            List files in bucket/prefix
  %b2 ls bucket/ --recursive       List all files recursively
  %b2 info bucket/path/file.csv    Show file metadata

File operations:
  %b2 upload local.csv bucket/remote.csv   Upload file
  %b2 download bucket/file.csv ./local.csv Download file
  %b2 cp bucket/src bucket/dst             Copy within B2
  %b2 rm bucket/path/file.csv              Delete file
  %b2 presign bucket/file --expires 3600   Pre-signed URL

Data loading:
  df = %b2_load bucket/data.csv            Load as pandas DataFrame
  df = %b2_load bucket/data.parquet --as polars  Load as Polars DataFrame
  text = %b2_load bucket/readme.md --as text     Load as string
  data = %b2_load bucket/model.bin --as bytes    Load as bytes
  obj = %b2_load bucket/config.json --as json    Load as Python dict

Data saving:
  %%b2_save bucket/output.csv
  df

  %%b2_save bucket/output.parquet
  df
"""
        print(help_text)

    # ─── Serialization helpers ─────────────────────────────────────────

    def _serialize_for_upload(self, obj: Any, file_key: str) -> bytes:
        """Serialize a Python object to bytes based on the target file extension."""
        from pathlib import PurePosixPath

        ext = PurePosixPath(file_key).suffix.lower()

        # If already bytes, return as-is
        if isinstance(obj, bytes):
            return obj
        if isinstance(obj, str):
            return obj.encode("utf-8")

        # Try pandas DataFrame
        try:
            import pandas as pd

            if isinstance(obj, pd.DataFrame):
                buffer = io.BytesIO()
                if ext == ".csv":
                    obj.to_csv(buffer, index=False)
                elif ext == ".parquet":
                    obj.to_parquet(buffer, index=False)
                elif ext in (".json", ".jsonl"):
                    buffer.write(obj.to_json(orient="records").encode("utf-8"))
                elif ext == ".feather":
                    obj.to_feather(buffer)
                else:
                    obj.to_csv(buffer, index=False)
                buffer.seek(0)
                return buffer.read()
        except ImportError:
            pass

        # Try polars DataFrame
        try:
            import polars as pl

            if isinstance(obj, pl.DataFrame):
                buffer = io.BytesIO()
                if ext == ".csv":
                    obj.write_csv(buffer)
                elif ext == ".parquet":
                    obj.write_parquet(buffer)
                elif ext in (".json", ".jsonl"):
                    obj.write_ndjson(buffer)
                elif ext == ".feather":
                    obj.write_ipc(buffer)
                else:
                    obj.write_csv(buffer)
                buffer.seek(0)
                return buffer.read()
        except ImportError:
            pass

        # Fallback: try JSON serialization, then str()
        import json

        try:
            return json.dumps(obj, indent=2, default=str).encode("utf-8")
        except (TypeError, ValueError):
            return str(obj).encode("utf-8")
