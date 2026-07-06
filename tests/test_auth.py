"""TokenManager tests: expiry skew, refresh locking, rotation persistence."""

from __future__ import annotations

import asyncio
import json
import time

import httpx
import pytest
import respx

from brightspace_mcp.auth import TokenManager, Tokens

from conftest import TOKEN_URL, make_cfg, write_token_file


@pytest.fixture
async def http():
    async with httpx.AsyncClient() as client:
        yield client


def test_expiry_skew():
    fresh = Tokens("a", "r", time.time() + 3600)
    nearly = Tokens("a", "r", time.time() + 30)  # inside the 60s skew window
    assert not fresh.is_expired
    assert nearly.is_expired


@respx.mock
async def test_concurrent_calls_refresh_exactly_once(tmp_path, http):
    cfg = make_cfg(tmp_path, expires_in=-10)  # already expired
    refresh = respx.post(TOKEN_URL).respond(
        200,
        json={"access_token": "tok2", "refresh_token": "ref2", "expires_in": 3600},
    )
    tm = TokenManager(cfg, http)
    tokens = await asyncio.gather(*(tm.get_access_token() for _ in range(5)))
    assert refresh.call_count == 1
    assert set(tokens) == {"tok2"}


@respx.mock
async def test_force_refresh_skipped_if_token_already_replaced(tmp_path, http):
    cfg = make_cfg(tmp_path)  # valid token "tok"
    tm = TokenManager(cfg, http)
    # Caller got a 401 with an old token; current token is already different.
    token = await tm.get_access_token(force_refresh=True, stale_token="old-token")
    assert token == "tok"  # no HTTP refresh happened (respx has no route registered)


@respx.mock
async def test_refresh_persists_rotated_token(tmp_path, http):
    cfg = make_cfg(tmp_path, expires_in=-10)
    respx.post(TOKEN_URL).respond(
        200,
        json={"access_token": "tok2", "refresh_token": "ref2", "expires_in": 3600},
    )
    tm = TokenManager(cfg, http)
    assert await tm.get_access_token() == "tok2"
    on_disk = json.loads(cfg.token_file.read_text())
    assert on_disk["refresh_token"] == "ref2"


@respx.mock
async def test_adopts_tokens_rotated_by_another_process(tmp_path, http):
    cfg = make_cfg(tmp_path)
    tm = TokenManager(cfg, http)
    # Simulate another process refreshing: new tokens on disk, ours now expired.
    write_token_file(cfg.token_file, access="tok-other", refresh="ref-other")
    tm._tokens.expires_at = time.time() - 10
    token = await tm.get_access_token()
    assert token == "tok-other"  # adopted from disk, no HTTP refresh (no respx route)
