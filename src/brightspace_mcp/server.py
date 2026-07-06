"""FastMCP server entry point for the Brightspace Admin MCP.

Run as a module:  python -m brightspace_mcp.server
Claude Code talks to it over stdio (see .mcp.json).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from .context import close_client
from .tools import register_all


@asynccontextmanager
async def _lifespan(_server: FastMCP) -> AsyncIterator[None]:
    try:
        yield
    finally:
        await close_client()


mcp = FastMCP("brightspace-admin", lifespan=_lifespan)
register_all(mcp)


def main() -> None:
    # stdio transport is what Claude Code / Claude Desktop use.
    mcp.run()


if __name__ == "__main__":
    main()
