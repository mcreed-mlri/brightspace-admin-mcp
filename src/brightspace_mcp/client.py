"""Async HTTP client for the Brightspace (Valence) REST API.

Responsibilities:
- inject the Bearer access token (via TokenManager) and refresh-and-retry once on 401
- resolve product API versions (lp/le) — from config, or auto-discovered from /d2l/api/versions/
- build URLs as {instance}/d2l/api/{product}/{version}{path}
- follow Brightspace's bookmark-based paging (PagedResultSet) up to a safe cap
"""

from __future__ import annotations

from typing import Any

import httpx

from .auth import TokenManager
from .config import Config

# Fallback versions used only if discovery fails and nothing is set in .env.
_DEFAULT_VERSIONS = {"lp": "1.43", "le": "1.74"}

# Safety cap so a runaway pagination loop can't fetch the entire org.
_MAX_PAGES = 50


class BrightspaceAPIError(RuntimeError):
    """A non-2xx response from the Brightspace API, with status and body for context."""

    def __init__(self, status: int, method: str, url: str, body: str):
        self.status = status
        super().__init__(f"{method} {url} -> {status}: {body[:1000]}")


class BrightspaceClient:
    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._http = httpx.AsyncClient(timeout=60, follow_redirects=True)
        self._tokens = TokenManager(cfg, self._http)
        self._versions: dict[str, str] = {}
        if cfg.lp_version:
            self._versions["lp"] = cfg.lp_version
        if cfg.le_version:
            self._versions["le"] = cfg.le_version

    async def aclose(self) -> None:
        await self._http.aclose()

    # --- version handling ---------------------------------------------------------
    async def list_versions(self) -> list[dict]:
        """Return the raw /d2l/api/versions/ payload (all products + supported versions)."""
        url = f"{self._cfg.api_root}/versions/"
        resp = await self._authed_request("GET", url)
        return resp.json()

    async def version_for(self, product: str) -> str:
        """Resolve the API version for a product ('lp' or 'le'), discovering if needed."""
        if product in self._versions:
            return self._versions[product]
        try:
            for entry in await self.list_versions():
                code = (entry.get("ProductCode") or "").lower()
                latest = entry.get("LatestVersion")
                if code and latest:
                    self._versions[code] = latest
        except Exception:
            pass  # fall back below
        return self._versions.get(product) or _DEFAULT_VERSIONS.get(product, "1.0")

    # --- core request helpers -----------------------------------------------------
    async def _authed_request(
        self, method: str, url: str, *, params: dict | None = None
    ) -> httpx.Response:
        token = await self._tokens.get_access_token()
        resp = await self._http.request(
            method, url, params=params, headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code == 401:
            # Token may have been revoked/expired early — refresh once and retry.
            token = await self._tokens.get_access_token(force_refresh=True)
            resp = await self._http.request(
                method, url, params=params, headers={"Authorization": f"Bearer {token}"}
            )
        if resp.status_code >= 400:
            raise BrightspaceAPIError(resp.status_code, method, url, resp.text)
        return resp

    async def get(
        self, product: str, path: str, params: dict | None = None
    ) -> Any:
        """GET {instance}/d2l/api/{product}/{version}{path} and return parsed JSON.

        `path` should start with '/' and NOT include the product/version prefix,
        e.g. product='lp', path='/users/whoami'.
        """
        version = await self.version_for(product)
        url = f"{self._cfg.api_root}/{product}/{version}{path}"
        resp = await self._authed_request("GET", url, params=params)
        if not resp.content:
            return None
        return resp.json()

    async def get_raw(self, path: str, params: dict | None = None) -> Any:
        """GET an arbitrary path under {instance}/d2l/api (escape hatch for exploration).

        `path` is appended to /d2l/api, e.g. '/lp/1.43/organization/info'.
        """
        url = f"{self._cfg.api_root}{path}"
        resp = await self._authed_request("GET", url, params=params)
        if not resp.content:
            return None
        ctype = resp.headers.get("content-type", "")
        return resp.json() if "json" in ctype else resp.text

    async def download(self, url: str, dest) -> None:
        """Stream a (possibly large) authenticated download to a local file path.

        `url` may be a full URL (as returned in Data Hub download links) or a path
        relative to the API root.
        """
        if not url.lower().startswith("http"):
            url = f"{self._cfg.api_root}{url}"
        # Force a refresh if near expiry so a long stream doesn't die mid-download.
        token = await self._tokens.get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        async with self._http.stream("GET", url, headers=headers) as resp:
            if resp.status_code >= 400:
                body = (await resp.aread()).decode("utf-8", "replace")
                raise BrightspaceAPIError(resp.status_code, "GET", url, body)
            with open(dest, "wb") as fh:
                async for chunk in resp.aiter_bytes():
                    fh.write(chunk)

    async def get_paged(
        self, product: str, path: str, params: dict | None = None
    ) -> list[Any]:
        """Follow Brightspace bookmark paging and return all Items combined.

        Works with the PagedResultSet shape: {PagingInfo: {Bookmark, HasMoreItems}, Items: [...]}.
        Stops at _MAX_PAGES to avoid pulling an entire org by accident.
        """
        params = dict(params or {})
        items: list[Any] = []
        for _ in range(_MAX_PAGES):
            page = await self.get(product, path, params=params)
            if page is None:
                break
            if isinstance(page, list):  # endpoint isn't actually paged
                items.extend(page)
                break
            items.extend(page.get("Items", []))
            paging = page.get("PagingInfo") or {}
            if not paging.get("HasMoreItems"):
                break
            params["bookmark"] = paging.get("Bookmark")
        return items
