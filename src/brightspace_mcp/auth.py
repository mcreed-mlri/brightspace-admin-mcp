"""OAuth 2.0 Authorization Code token management.

Brightspace ROTATES refresh tokens: every refresh returns a brand-new refresh token and
invalidates the old one. So we must persist the new refresh token to disk immediately after
every refresh, or the next run will fail with an invalid_grant error.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from .config import TOKEN_URL, Config

# Refresh a bit early so we never hand out a token that expires mid-request.
_EXPIRY_SKEW_SECONDS = 60


class AuthError(RuntimeError):
    """Raised when authorization is missing or a token request fails."""


@dataclass
class Tokens:
    access_token: str
    refresh_token: str
    expires_at: float  # epoch seconds

    @property
    def is_expired(self) -> bool:
        return time.time() >= (self.expires_at - _EXPIRY_SKEW_SECONDS)

    def to_dict(self) -> dict:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_token_response(cls, data: dict) -> "Tokens":
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=time.time() + float(data.get("expires_in", 3600)),
        )


def _read_tokens(path: Path) -> Tokens | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Tokens(
        access_token=raw["access_token"],
        refresh_token=raw["refresh_token"],
        expires_at=float(raw["expires_at"]),
    )


def _write_tokens(path: Path, tokens: Tokens) -> None:
    path.write_text(json.dumps(tokens.to_dict(), indent=2), encoding="utf-8")


def exchange_code(cfg: Config, code: str, client: httpx.Client | None = None) -> Tokens:
    """One-time: trade an authorization code for the first access + refresh tokens.

    Used by scripts/authorize.py. Persists the result to the configured token file.
    """
    owns_client = client is None
    client = client or httpx.Client(timeout=30)
    try:
        resp = client.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": cfg.redirect_uri,
                "client_id": cfg.client_id,
                "client_secret": cfg.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    finally:
        if owns_client:
            client.close()
    if resp.status_code != 200:
        raise AuthError(f"Code exchange failed ({resp.status_code}): {resp.text}")
    tokens = Tokens.from_token_response(resp.json())
    _write_tokens(cfg.token_file, tokens)
    return tokens


class TokenManager:
    """Holds the current tokens and refreshes them on demand (async, for the server)."""

    def __init__(self, cfg: Config, http_client: httpx.AsyncClient):
        self._cfg = cfg
        self._http = http_client
        self._tokens: Tokens | None = _read_tokens(cfg.token_file)

    async def get_access_token(self, force_refresh: bool = False) -> str:
        if self._tokens is None:
            raise AuthError(
                "No tokens found. Run `python scripts/authorize.py` once to authorize."
            )
        if force_refresh or self._tokens.is_expired:
            await self._refresh()
        return self._tokens.access_token

    async def _refresh(self) -> None:
        assert self._tokens is not None
        resp = await self._http.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._tokens.refresh_token,
                "client_id": self._cfg.client_id,
                "client_secret": self._cfg.client_secret,
                "scope": self._cfg.scope,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code != 200:
            raise AuthError(
                f"Token refresh failed ({resp.status_code}): {resp.text}\n"
                "If this is invalid_grant, re-run `python scripts/authorize.py`."
            )
        self._tokens = Tokens.from_token_response(resp.json())
        # CRITICAL: persist the rotated refresh token before we do anything else.
        _write_tokens(self._cfg.token_file, self._tokens)
