"""Manual fallback: exchange an authorization code (or full callback URL) for tokens.

Use this when the local HTTPS listener fails but you can still see the
`...callback?code=...` URL in your browser:

    python scripts/exchange.py "ac.us-east-1.XXXX"
    python scripts/exchange.py "https://localhost:3000/callback?code=ac...&state=..."

The authorization code is single-use and expires quickly, so run this right away.
"""

from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from brightspace_mcp.auth import exchange_code  # noqa: E402
from brightspace_mcp.config import load_config  # noqa: E402


def _extract_code(arg: str) -> str:
    if arg.lower().startswith("http"):
        qs = urllib.parse.urlparse(arg).query
        code = urllib.parse.parse_qs(qs).get("code", [""])[0]
        if not code:
            raise SystemExit("No ?code= found in the URL.")
        return code
    return arg.strip()


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python scripts/exchange.py "<code or full callback URL>"', file=sys.stderr)
        return 2
    cfg = load_config()
    code = _extract_code(sys.argv[1])
    tokens = exchange_code(cfg, code)
    print(f"Success. Tokens saved to {cfg.token_file}")
    print(f"Access token expires at epoch {int(tokens.expires_at)}.")
    print("Now run: python scripts/smoke.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
