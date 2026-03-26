"""Rich display formatters for B2 magic command output in Jupyter."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

from IPython.display import HTML, display


def _human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable size string."""
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024  # type: ignore[assignment]
    return f"{size_bytes:.1f} EB"


def _format_timestamp(ms: int | None) -> str:
    """Convert B2 millisecond timestamp to readable string."""
    if ms is None:
        return "—"
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def display_file_list(files: Sequence[dict[str, Any]], bucket_name: str, prefix: str) -> None:
    """Display a list of files as a rich HTML table.

    Parameters
    ----------
        files: List of file info dicts from B2 listing.
        bucket_name: Name of the bucket.
        prefix: Current path prefix.
    """
    if not files:
        display(HTML(f"<p><em>No files found in <code>{bucket_name}/{prefix}</code></em></p>"))
        return

    total_size = sum(f.get("size", 0) for f in files)
    rows = []
    for f in files:
        name = f.get("name", f.get("fileName", ""))
        if prefix and name.startswith(prefix):
            name = name[len(prefix) :]
        is_dir = name.endswith("/")
        icon = "📁" if is_dir else "📄"
        size = "—" if is_dir else _human_size(f.get("size", 0))
        modified = _format_timestamp(f.get("uploadTimestamp"))
        rows.append(f"<tr><td>{icon} {name}</td><td>{size}</td><td>{modified}</td></tr>")

    html = f"""
    <div style="margin: 8px 0;">
        <strong>b2://{bucket_name}/{prefix}</strong>
        <span style="color: #666; margin-left: 12px;">
            {len(files)} items &middot; {_human_size(total_size)} total
        </span>
    </div>
    <table style="border-collapse: collapse; width: 100%; font-size: 13px;">
        <thead>
            <tr style="border-bottom: 2px solid #ddd; text-align: left;">
                <th style="padding: 6px 12px;">Name</th>
                <th style="padding: 6px 12px; width: 100px;">Size</th>
                <th style="padding: 6px 12px; width: 180px;">Modified</th>
            </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
    </table>
    """
    display(HTML(html))


def display_buckets(buckets: Sequence[dict[str, Any]]) -> None:
    """Display a list of buckets as a rich HTML table."""
    if not buckets:
        display(HTML("<p><em>No buckets found.</em></p>"))
        return

    rows = []
    for b in buckets:
        name = b.get("name", "")
        bucket_type = b.get("type", "")
        icon = "🔒" if bucket_type == "allPrivate" else "🌐"
        rows.append(f"<tr><td>{icon} <code>{name}</code></td><td>{bucket_type}</td></tr>")

    html = f"""
    <div style="margin: 8px 0;">
        <strong>B2 Buckets</strong>
        <span style="color: #666; margin-left: 12px;">{len(buckets)} buckets</span>
    </div>
    <table style="border-collapse: collapse; width: 100%; font-size: 13px;">
        <thead>
            <tr style="border-bottom: 2px solid #ddd; text-align: left;">
                <th style="padding: 6px 12px;">Bucket</th>
                <th style="padding: 6px 12px; width: 120px;">Type</th>
            </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
    </table>
    """
    display(HTML(html))


def display_file_info(info: dict[str, Any]) -> None:
    """Display detailed file metadata as a rich HTML card."""
    name = info.get("fileName", info.get("name", "unknown"))
    html = f"""
    <div style="border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 8px 0;
                max-width: 500px; font-size: 13px;">
        <div style="font-size: 15px; font-weight: bold; margin-bottom: 12px;">
            📄 {name}
        </div>
        <table style="width: 100%;">
            <tr><td style="color: #666; padding: 3px 0;">Size</td>
                <td>{_human_size(info.get("size", 0))}</td></tr>
            <tr><td style="color: #666; padding: 3px 0;">Content Type</td>
                <td>{info.get("contentType", "—")}</td></tr>
            <tr><td style="color: #666; padding: 3px 0;">Upload Date</td>
                <td>{_format_timestamp(info.get("uploadTimestamp"))}</td></tr>
            <tr><td style="color: #666; padding: 3px 0;">File ID</td>
                <td><code style="font-size: 11px;">{info.get("fileId", "—")}</code></td></tr>
            <tr><td style="color: #666; padding: 3px 0;">SHA1</td>
                <td><code style="font-size: 11px;">{info.get("contentSha1", "—")}</code></td></tr>
            <tr><td style="color: #666; padding: 3px 0;">Action</td>
                <td>{info.get("action", "—")}</td></tr>
        </table>
    </div>
    """
    display(HTML(html))


def display_auth_status(
    authenticated: bool,
    account_id: str = "",
    api_url: str = "",
    allowed_bucket: str = "",
) -> None:
    """Display authentication status."""
    if authenticated:
        html = f"""
        <div style="border: 1px solid #4CAF50; border-radius: 8px; padding: 12px;
                    margin: 8px 0; background: #f0fff0; font-size: 13px;">
            <strong style="color: #4CAF50;">✅ Authenticated</strong>
            <table style="margin-top: 8px;">
                <tr><td style="color: #666; padding: 2px 8px 2px 0;">Account</td>
                    <td><code>{account_id}</code></td></tr>
                <tr><td style="color: #666; padding: 2px 8px 2px 0;">API URL</td>
                    <td><code>{api_url}</code></td></tr>
                <tr><td style="color: #666; padding: 2px 8px 2px 0;">Bucket</td>
                    <td>{allowed_bucket or "All buckets"}</td></tr>
            </table>
        </div>
        """
    else:
        html = """
        <div style="border: 1px solid #f44336; border-radius: 8px; padding: 12px;
                    margin: 8px 0; background: #fff0f0; font-size: 13px;">
            <strong style="color: #f44336;">❌ Not authenticated</strong>
            <div style="margin-top: 8px;">
                Use <code>%b2 auth --key-id &lt;id&gt; --key &lt;key&gt;</code>
                or set <code>B2_APPLICATION_KEY_ID</code> / <code>B2_APPLICATION_KEY</code>
            </div>
        </div>
        """
    display(HTML(html))


def display_upload_success(local_path: str, b2_path: str, size: int, file_id: str) -> None:
    """Display upload success message."""
    html = f"""
    <div style="border: 1px solid #4CAF50; border-radius: 8px; padding: 12px;
                margin: 8px 0; background: #f0fff0; font-size: 13px;">
        <strong style="color: #4CAF50;">✅ Uploaded successfully</strong>
        <table style="margin-top: 8px;">
            <tr><td style="color: #666; padding: 2px 8px 2px 0;">From</td>
                <td><code>{local_path}</code></td></tr>
            <tr><td style="color: #666; padding: 2px 8px 2px 0;">To</td>
                <td><code>b2://{b2_path}</code></td></tr>
            <tr><td style="color: #666; padding: 2px 8px 2px 0;">Size</td>
                <td>{_human_size(size)}</td></tr>
            <tr><td style="color: #666; padding: 2px 8px 2px 0;">File ID</td>
                <td><code style="font-size: 11px;">{file_id}</code></td></tr>
        </table>
    </div>
    """
    display(HTML(html))


def display_download_success(b2_path: str, local_path: str, size: int) -> None:
    """Display download success message."""
    html = f"""
    <div style="border: 1px solid #2196F3; border-radius: 8px; padding: 12px;
                margin: 8px 0; background: #f0f7ff; font-size: 13px;">
        <strong style="color: #2196F3;">⬇️ Downloaded successfully</strong>
        <table style="margin-top: 8px;">
            <tr><td style="color: #666; padding: 2px 8px 2px 0;">From</td>
                <td><code>b2://{b2_path}</code></td></tr>
            <tr><td style="color: #666; padding: 2px 8px 2px 0;">To</td>
                <td><code>{local_path}</code></td></tr>
            <tr><td style="color: #666; padding: 2px 8px 2px 0;">Size</td>
                <td>{_human_size(size)}</td></tr>
        </table>
    </div>
    """
    display(HTML(html))
