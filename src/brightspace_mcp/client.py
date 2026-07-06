"""Async HTTP client for the Brightspace (Valence) REST API.

Responsibilities:
- inject the Bearer access token (via TokenManager) and refresh-and-retry once on 401
- resolve product API versions (lp/le) — from config, or auto-discovered from /d2l/api/versions/
- build URLs as {instance}/d2l/api/{product}/{version}{path}
- follow Brightspace's bookmark-based paging (PagedResultSet) up to a safe cap
- append every request to a local audit log (who/what/when for compliance review)
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from .auth import TokenManager
from .config import PROJECT_ROOT, Config

# Fallback versions used only if discovery fails and nothing is set in .env.
_DEFAULT_VERSIONS = {"lp": "1.43", "le": "1.74"}

# Safety cap so a runaway pagination loop can't fetch the entire org.
_MAX_PAGES = 50

# Default cap on items returned to the model — protects the conversation context
# from a broad search dumping thousands of records. Callers can raise it explicitly.
DEFAULT_MAX_ITEMS = 200

_AUDIT_LOG = PROJECT_ROOT / "audit.log"


class BrightspaceAPIError(RuntimeError):
    """A non-2xx response from the Brightspace API, with status and body for context."""

    def __init__(self, status: int, method: str, url: str, body: str):
        self.status = status
        super().__init__(f"{method} {url} -> {status}: {body[:1000]}")


def _audit(method: str, url: str, status: int) -> None:
    """Append one JSON line per API call to audit.log (never stdout — stdio transport).

    Best-effort: an unwritable log must never break an API call.
    """
    try:
        line = json.dumps(
            {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "method": method,
                "url": url,
                "status": status,
            }
        )
        with open(_AUDIT_LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


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
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        json_body: Any = None,
    ) -> httpx.Response:
        token = await self._tokens.get_access_token()
        resp = await self._http.request(
            method,
            url,
            params=params,
            json=json_body,
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 401:
            # Token may have been revoked/expired early — refresh once and retry.
            token = await self._tokens.get_access_token(
                force_refresh=True, stale_token=token
            )
            resp = await self._http.request(
                method,
                url,
                params=params,
                json=json_body,
                headers={"Authorization": f"Bearer {token}"},
            )
        _audit(method, url, resp.status_code)
        if resp.status_code >= 400:
            raise BrightspaceAPIError(resp.status_code, method, url, resp.text)
        return resp

    async def post(self, product: str, path: str, body: Any = None) -> Any:
        """POST {instance}/d2l/api/{product}/{version}{path} with a JSON body."""
        version = await self.version_for(product)
        url = f"{self._cfg.api_root}/{product}/{version}{path}"
        resp = await self._authed_request("POST", url, json_body=body)
        if not resp.content:
            return None
        return resp.json()

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

        `path` is appended to /d2l/api, e.g. '/lp/1.43/organization/info'. A full URL
        is accepted as-is when it targets this instance (used to follow paging links).
        """
        if path.lower().startswith("http"):
            if not path.startswith(self._cfg.instance_url):
                raise ValueError(f"Refusing to call a URL outside {self._cfg.instance_url}")
            url = path
        else:
            url = f"{self._cfg.api_root}{path}"
        resp = await self._authed_request("GET", url, params=params)
        if not resp.content:
            return None
        ctype = resp.headers.get("content-type", "")
        return resp.json() if "json" in ctype else resp.text

    async def download(self, url: str, dest) -> None:
        """Stream a (possibly large) authenticated download to a local file path.

        `url` may be a full URL (as returned in Data Hub download links) or a path
        relative to the API root. Retries once with a fresh token on 401.
        """
        if not url.lower().startswith("http"):
            url = f"{self._cfg.api_root}{url}"
        token = await self._tokens.get_access_token()
        for attempt in range(2):
            async with self._http.stream(
                "GET", url, headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                if resp.status_code == 401 and attempt == 0:
                    await resp.aread()
                    token = await self._tokens.get_access_token(
                        force_refresh=True, stale_token=token
                    )
                    continue
                _audit("GET", url, resp.status_code)
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "replace")
                    raise BrightspaceAPIError(resp.status_code, "GET", url, body)
                with open(dest, "wb") as fh:
                    async for chunk in resp.aiter_bytes():
                        fh.write(chunk)
                return

    async def get_paged(
        self,
        product: str,
        path: str,
        params: dict | None = None,
        max_items: int = DEFAULT_MAX_ITEMS,
    ) -> dict:
        """Follow Brightspace bookmark paging and return a result envelope.

        Works with the PagedResultSet shape: {PagingInfo: {Bookmark, HasMoreItems}, Items: [...]}.
        Returns {"items": [...], "count": N, "truncated": bool} — truncated means more
        results exist server-side than the max_items cap allowed us to return.
        """
        params = dict(params or {})
        items: list[Any] = []
        truncated = False
        for _ in range(_MAX_PAGES):
            page = await self.get(product, path, params=params)
            if page is None:
                break
            if isinstance(page, list):  # endpoint isn't actually paged
                items.extend(page)
                break
            items.extend(page.get("Items", []))
            paging = page.get("PagingInfo") or {}
            bookmark = paging.get("Bookmark")
            # Missing bookmark with HasMoreItems would loop on the same page — stop.
            if not paging.get("HasMoreItems") or not bookmark:
                break
            if len(items) >= max_items:
                truncated = True
                break
            params["bookmark"] = bookmark
        else:
            truncated = True  # hit _MAX_PAGES with more pages remaining
        if len(items) > max_items:
            items = items[:max_items]
            truncated = True
        return {"items": items, "count": len(items), "truncated": truncated}
