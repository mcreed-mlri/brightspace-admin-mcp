"""Configuration loaded from environment / .env.

All Brightspace-specific constants and the user's instance settings live here so the
rest of the code never hardcodes URLs or reads os.environ directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Project root = two levels up from this file (src/brightspace_mcp/config.py -> root)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load .env from the project root regardless of the current working directory.
load_dotenv(PROJECT_ROOT / ".env")

# --- Fixed Brightspace OAuth 2.0 endpoints (same for all instances) ---------------
# https://docs.valence.desire2learn.com/basic/oauth2.html
AUTH_URL = "https://auth.brightspace.com/oauth2/auth"
TOKEN_URL = "https://auth.brightspace.com/core/connect/token"


class ConfigError(RuntimeError):
    """Raised when required configuration is missing."""


def flag(name: str, default: bool) -> bool:
    """Read a boolean feature flag from the environment ('0'/'false'/'no'/'off' = off)."""
    val = os.environ.get(name, "").strip().lower()
    if not val:
        return default
    return val not in ("0", "false", "no", "off")


def _require(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise ConfigError(
            f"Missing required setting {name}. Copy .env.example to .env and fill it in."
        )
    return val


@dataclass(frozen=True)
class Config:
    instance_url: str
    client_id: str
    client_secret: str
    scope: str
    redirect_uri: str
    token_file: Path
    lp_version: str | None
    le_version: str | None

    @property
    def api_root(self) -> str:
        return f"{self.instance_url}/d2l/api"


def load_config() -> Config:
    """Build a Config from environment variables, validating required fields."""
    instance = _require("BRIGHTSPACE_INSTANCE_URL").rstrip("/")

    token_file = os.environ.get("BRIGHTSPACE_TOKEN_FILE", ".tokens.json").strip()
    token_path = Path(token_file)
    if not token_path.is_absolute():
        token_path = PROJECT_ROOT / token_path

    def _opt(name: str) -> str | None:
        v = os.environ.get(name, "").strip()
        return v or None

    return Config(
        instance_url=instance,
        client_id=_require("BRIGHTSPACE_CLIENT_ID"),
        client_secret=_require("BRIGHTSPACE_CLIENT_SECRET"),
        scope=_require("BRIGHTSPACE_SCOPE"),
        redirect_uri=os.environ.get(
            "BRIGHTSPACE_REDIRECT_URI", "https://localhost:3000/callback"
        ).strip(),
        token_file=token_path,
        lp_version=_opt("BRIGHTSPACE_LP_VERSION"),
        le_version=_opt("BRIGHTSPACE_LE_VERSION"),
    )
