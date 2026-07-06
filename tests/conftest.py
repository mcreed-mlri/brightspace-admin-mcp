"""Shared fixtures: a fake Config + token file, and an isolated audit log."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

import brightspace_mcp.client as client_mod
from brightspace_mcp.config import Config

BASE = "https://test.brightspace.com"
TOKEN_URL = "https://auth.brightspace.com/core/connect/token"


@pytest.fixture(autouse=True)
def isolated_audit_log(tmp_path, monkeypatch):
    monkeypatch.setattr(client_mod, "_AUDIT_LOG", tmp_path / "audit.log")


def write_token_file(path: Path, *, access="tok", refresh="ref", expires_in=3600.0) -> None:
    path.write_text(
        json.dumps(
            {
                "access_token": access,
                "refresh_token": refresh,
                "expires_at": time.time() + expires_in,
            }
        ),
        encoding="utf-8",
    )


def make_cfg(tmp_path: Path, *, lp_version: str | None = "1.43", **token_kwargs) -> Config:
    token_file = tmp_path / "tokens.json"
    write_token_file(token_file, **token_kwargs)
    return Config(
        instance_url=BASE,
        client_id="cid",
        client_secret="secret",
        scope="core:*:*",
        redirect_uri="https://localhost:3000/callback",
        token_file=token_file,
        lp_version=lp_version,
        le_version="1.74",
    )


@pytest.fixture
def cfg(tmp_path) -> Config:
    return make_cfg(tmp_path)
