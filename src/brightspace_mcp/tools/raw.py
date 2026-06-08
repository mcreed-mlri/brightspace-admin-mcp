"""Raw GET escape hatch — call any Valence endpoint without writing a dedicated tool."""

from __future__ import annotations

from ..context import get_client


def register(mcp) -> None:
    @mcp.tool()
    async def api_get(path: str, params: dict | None = None) -> object:
        """Perform a raw GET against any Brightspace API path (read-only).

        `path` is everything after /d2l/api, including product + version, e.g.
        '/lp/1.43/organization/info' or '/le/1.74/12345/content/toc'.
        Returns parsed JSON (or text for non-JSON responses). Great for exploring
        endpoints from the Valence docs that don't yet have a dedicated tool.
        """
        return await get_client().get_raw(path, params=params)

    @mcp.tool()
    async def list_api_versions() -> list[dict]:
        """List all API products and their supported/latest versions on this instance."""
        return await get_client().list_versions()
