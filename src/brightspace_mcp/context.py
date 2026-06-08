"""Lazily-created shared BrightspaceClient.

Created on first use (not at import time) so that importing the tool modules never
requires .env to be present — useful for `--help` and discovery.
"""

from __future__ import annotations

from .client import BrightspaceClient
from .config import load_config

_client: BrightspaceClient | None = None


def get_client() -> BrightspaceClient:
    global _client
    if _client is None:
        _client = BrightspaceClient(load_config())
    return _client
