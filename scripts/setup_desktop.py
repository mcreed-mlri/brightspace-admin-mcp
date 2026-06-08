"""Add the Brightspace MCP to Claude Desktop's config.

Run after installing Claude Desktop:

    python scripts/setup_desktop.py

Edits %APPDATA%\\Claude\\claude_desktop_config.json to register the brightspace server.
Claude Desktop must be restarted afterward for changes to take effect.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APPDATA = Path(os.environ.get("APPDATA", ""))
CONFIG_PATH = APPDATA / "Claude" / "claude_desktop_config.json"

SERVER_ENTRY = {
    "command": "c:/dev/brightspace-admin-mcp/.venv/Scripts/python.exe",
    "args": ["-m", "brightspace_mcp.server"],
    "cwd": "c:/dev/brightspace-admin-mcp",
    "env": {"PYTHONPATH": "c:/dev/brightspace-admin-mcp/src"},
}


def main() -> int:
    if not CONFIG_PATH.parent.exists():
        print(
            f"Claude Desktop config folder not found: {CONFIG_PATH.parent}\n"
            "Install Claude Desktop from https://claude.ai/download, sign in, then re-run this script.",
            file=sys.stderr,
        )
        return 1

    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    else:
        config = {}

    servers = config.setdefault("mcpServers", {})

    if "brightspace" in servers:
        print("brightspace server entry already exists — updating it.")

    servers["brightspace"] = SERVER_ENTRY
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"Written to {CONFIG_PATH}")
    print("Restart Claude Desktop for changes to take effect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
