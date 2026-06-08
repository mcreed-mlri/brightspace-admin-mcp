"""One-time OAuth 2.0 Authorization Code flow.

Run once after filling in .env:

    python scripts/authorize.py

Opens your browser to Brightspace. After you log in and consent, Brightspace redirects
to https://localhost:3000/callback?code=... — Chrome will show an SSL error page (the
local server doesn't exist), but the code is already in the URL. Copy the full URL from
the address bar and paste it when prompted. That's it.
"""

from __future__ import annotations

import secrets
import sys
import urllib.parse
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from brightspace_mcp.auth import exchange_code  # noqa: E402
from brightspace_mcp.config import AUTH_URL, load_config  # noqa: E402


def _extract_code(raw: str) -> tuple[str, str]:
    """Return (code, state) from either a bare code or a full callback URL."""
    raw = raw.strip()
    if raw.lower().startswith("http"):
        qs = urllib.parse.urlparse(raw).query
        params = urllib.parse.parse_qs(qs)
        code = params.get("code", [""])[0]
        state = params.get("state", [""])[0]
        if not code:
            raise SystemExit("No ?code= found in the URL you pasted.")
        return code, state
    return raw, ""


def main() -> int:
    cfg = load_config()
    state = secrets.token_urlsafe(16)
    auth_url = AUTH_URL + "?" + urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": cfg.client_id,
            "redirect_uri": cfg.redirect_uri,
            "scope": cfg.scope,
            "state": state,
            "prompt": "consent",  # force fresh consent so scope changes take effect
        }
    )

    print("Opening your browser to Brightspace for authorization...")
    print("(If it doesn't open automatically, paste this URL into your browser:)")
    print(f"\n  {auth_url}\n")
    webbrowser.open(auth_url)

    print("After you log in and approve access, your browser will be redirected to")
    print(f"  {cfg.redirect_uri}?code=...")
    print("Chrome will show an SSL error page — that's fine. The code is in the URL.")
    print("\nCopy the full URL from your browser's address bar and paste it below.")
    print("(Or paste just the code= value if you prefer.)\n")

    try:
        raw = input("Paste callback URL or code: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.", file=sys.stderr)
        return 1

    if not raw:
        print("Nothing entered. Aborting.", file=sys.stderr)
        return 1

    code, received_state = _extract_code(raw)

    if received_state and received_state != state:
        print("Warning: state mismatch (possible CSRF or you pasted an old URL).")
        confirm = input("Continue anyway? [y/N]: ").strip().lower()
        if confirm != "y":
            return 1

    tokens = exchange_code(cfg, code)
    print(f"\nSuccess. Tokens saved to {cfg.token_file}")
    print("Now run: python scripts/smoke.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
