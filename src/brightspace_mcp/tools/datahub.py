"""Data Hub tools: Brightspace Data Sets (BDS) and Advanced Data Sets exports.

These are org-wide bulk CSV/zip exports for analytics. Listing is cheap; downloads can be
large and may contain PII — they are saved to ./exports/ (gitignored) by default.
"""

from __future__ import annotations

from pathlib import Path

from ..config import PROJECT_ROOT
from ..context import get_client


def register(mcp) -> None:
    @mcp.tool()
    async def list_brightspace_data_sets() -> list[dict]:
        """List available Brightspace Data Sets (BDS) — the standard bulk exports.

        Each entry includes a name, PluginId, and download link(s) for full/differential CSVs.
        """
        result = await get_client().get("lp", "/dataExport/bds")
        # Endpoint may return a bare list or a paged object depending on version.
        if isinstance(result, dict):
            return result.get("Objects", result.get("Items", []))
        return result or []

    @mcp.tool()
    async def list_advanced_data_sets() -> list[dict]:
        """List Advanced Data Sets available to export (custom/on-demand data exports)."""
        result = await get_client().get("lp", "/dataExport/list")
        if isinstance(result, dict):
            return result.get("Objects", result.get("Items", []))
        return result or []

    @mcp.tool()
    async def download_data_set(download_url: str, filename: str | None = None) -> str:
        """Download a data set export to ./exports/ given its download link.

        Pass a download link from list_brightspace_data_sets()/list_advanced_data_sets().
        Returns the local file path. WARNING: these files can be large and contain PII.
        """
        dest_dir = PROJECT_ROOT / "exports"
        dest_dir.mkdir(exist_ok=True)
        name = filename or download_url.rstrip("/").split("/")[-1] or "dataset.zip"
        dest = dest_dir / name
        await get_client().download(download_url, dest)
        return str(dest)
