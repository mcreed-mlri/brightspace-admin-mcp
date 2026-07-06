"""Client tests: bookmark paging, max_items cap, version resolution, 401 retry."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from brightspace_mcp.client import BrightspaceClient

from conftest import BASE, TOKEN_URL, make_cfg

ORG_URL = f"{BASE}/d2l/api/lp/1.43/orgstructure/"


@pytest.fixture
async def client(cfg):
    c = BrightspaceClient(cfg)
    yield c
    await c.aclose()


def _page(items, bookmark=None, more=False):
    return httpx.Response(
        200,
        json={"PagingInfo": {"Bookmark": bookmark, "HasMoreItems": more}, "Items": items},
    )


@respx.mock
async def test_get_paged_follows_bookmarks(client):
    route = respx.get(ORG_URL)
    route.side_effect = [
        _page([1, 2], bookmark="b1", more=True),
        _page([3], bookmark="b2", more=False),
    ]
    result = await client.get_paged("lp", "/orgstructure/")
    assert result == {"items": [1, 2, 3], "count": 3, "truncated": False}
    assert route.calls[1].request.url.params["bookmark"] == "b1"


@respx.mock
async def test_get_paged_caps_at_max_items(client):
    route = respx.get(ORG_URL)
    route.side_effect = [
        _page([1, 2], bookmark="b1", more=True),
        _page([3, 4], bookmark="b2", more=True),
    ]
    result = await client.get_paged("lp", "/orgstructure/", max_items=3)
    assert result == {"items": [1, 2, 3], "count": 3, "truncated": True}
    assert route.call_count == 2  # did not fetch a third page


@respx.mock
async def test_get_paged_handles_bare_list_endpoint(client):
    respx.get(ORG_URL).respond(200, json=[1, 2])
    result = await client.get_paged("lp", "/orgstructure/")
    assert result == {"items": [1, 2], "count": 2, "truncated": False}


@respx.mock
async def test_get_paged_stops_on_missing_bookmark(client):
    # HasMoreItems claims more but no bookmark — must not loop on the same page.
    route = respx.get(ORG_URL)
    route.side_effect = [_page([1], bookmark=None, more=True)]
    result = await client.get_paged("lp", "/orgstructure/")
    assert result["items"] == [1]
    assert route.call_count == 1


@respx.mock
async def test_version_discovery_and_fallback(tmp_path):
    cfg = make_cfg(tmp_path, lp_version=None)
    client = BrightspaceClient(cfg)
    try:
        respx.get(f"{BASE}/d2l/api/versions/").respond(
            200, json=[{"ProductCode": "lp", "LatestVersion": "1.50"}]
        )
        assert await client.version_for("lp") == "1.50"
    finally:
        await client.aclose()

    # Discovery failure falls back to the baked-in default.
    client = BrightspaceClient(make_cfg(tmp_path, lp_version=None))
    try:
        respx.get(f"{BASE}/d2l/api/versions/").respond(500, text="boom")
        assert await client.version_for("lp") == "1.43"
    finally:
        await client.aclose()


@respx.mock
async def test_401_refreshes_once_and_retries(client, cfg):
    whoami = f"{BASE}/d2l/api/lp/1.43/users/whoami"
    route = respx.get(whoami)
    route.side_effect = [
        httpx.Response(401, text="expired"),
        httpx.Response(200, json={"Identifier": "1"}),
    ]
    refresh = respx.post(TOKEN_URL).respond(
        200,
        json={"access_token": "tok2", "refresh_token": "ref2", "expires_in": 3600},
    )
    result = await client.get("lp", "/users/whoami")
    assert result == {"Identifier": "1"}
    assert refresh.call_count == 1
    assert route.calls[1].request.headers["Authorization"] == "Bearer tok2"
    # Rotated refresh token must be persisted.
    assert json.loads(cfg.token_file.read_text())["refresh_token"] == "ref2"
