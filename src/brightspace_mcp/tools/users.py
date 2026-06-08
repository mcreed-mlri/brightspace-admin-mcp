"""User lookup tools (Learning Platform API)."""

from __future__ import annotations

from ..context import get_client


def register(mcp) -> None:
    @mcp.tool()
    async def whoami() -> dict:
        """Return the Brightspace user the MCP is acting as (Identifier, names, role).

        Good first call to confirm auth and that you're acting with admin privileges.
        """
        return await get_client().get("lp", "/users/whoami")

    @mcp.tool()
    async def get_user(user_id: int) -> dict:
        """Get a single user's profile by their Brightspace UserId."""
        return await get_client().get("lp", f"/users/{user_id}")

    @mcp.tool()
    async def find_user(
        username: str | None = None,
        org_defined_id: str | None = None,
        external_email: str | None = None,
    ) -> list[dict]:
        """Find user(s) by username, OrgDefinedId, or external email.

        Provide exactly one filter. Returns matching user records.
        """
        params: dict = {}
        if username:
            params["userName"] = username
        if org_defined_id:
            params["orgDefinedId"] = org_defined_id
        if external_email:
            params["externalEmail"] = external_email
        if not params:
            raise ValueError("Provide one of: username, org_defined_id, external_email.")
        result = await get_client().get("lp", "/users/", params=params)
        # This endpoint returns either a single object or a list depending on the filter.
        if result is None:
            return []
        return result if isinstance(result, list) else [result]
