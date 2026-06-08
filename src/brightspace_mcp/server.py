"""FastMCP server entry point for the Brightspace Admin MCP.

Run as a module:  python -m brightspace_mcp.server
Claude Code talks to it over stdio (see .mcp.json).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .tools import register_all

mcp = FastMCP("brightspace-admin")
register_all(mcp)


def main() -> None:
    # stdio transport is what Claude Code / Claude Desktop use.
    mcp.run()


if __name__ == "__main__":
    main()
