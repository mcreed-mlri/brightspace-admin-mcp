"""Quick connectivity test, independent of Claude.

    python scripts/smoke.py            # calls whoami
    python scripts/smoke.py --versions # lists supported API versions

Run it twice to confirm the rotating refresh token is being persisted correctly.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from brightspace_mcp.client import BrightspaceClient  # noqa: E402
from brightspace_mcp.config import load_config  # noqa: E402


async def run(show_versions: bool) -> int:
    client = BrightspaceClient(load_config())
    try:
        if show_versions:
            print(json.dumps(await client.list_versions(), indent=2))
        else:
            me = await client.get("lp", "/users/whoami")
            print(json.dumps(me, indent=2))
            print("\nAuth + API OK.")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        await client.aclose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run("--versions" in sys.argv)))
