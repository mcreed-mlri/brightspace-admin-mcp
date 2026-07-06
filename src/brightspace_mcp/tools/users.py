"""User lookup tools (Learning Platform API)."""

from __future__ import annotations

from mcp.types import ToolAnnotations

from ..client import BrightspaceAPIError
from ..context import get_client

_READ_ONLY = ToolAnnotations(readOnlyHint=True)


def register(mcp) -> None:
    @mcp.tool(annotations=_READ_ONLY)
    async def whoami() -> dict:
        """Return the Brightspace user the MCP is acting as (Identifier, names, role).

        Good first call to confirm auth and that you're acting with admin privileges.
        """
        return await get_client().get("lp", "/users/whoami")

    @mcp.tool(annotations=_READ_ONLY)
    async def get_user(user_id: int) -> dict:
        """Get a single user's profile by their Brightspace UserId."""
        return await get_client().get("lp", f"/users/{user_id}")

    @mcp.tool(annotations=_READ_ONLY)
    async def find_user(
        username: str | None = None,
        org_defined_id: str | None = None,
        external_email: str | None = None,
    ) -> list[dict]:
        """Find user(s) by username, OrgDefinedId, or external email.

        Provide exactly one filter. Returns matching user records.
        """
        filters = {
            "userName": username,
            "orgDefinedId": org_defined_id,
            "externalEmail": external_email,
        }
        params = {k: v for k, v in filters.items() if v}
        if len(params) != 1:
            raise ValueError(
                "Provide exactly one of: username, org_defined_id, external_email."
            )
        try:
            result = await get_client().get("lp", "/users/", params=params)
        except BrightspaceAPIError as exc:
            if exc.status == 404:
                return []  # Brightspace answers 404 when no user matches the filter
            raise
        # Shape varies by filter: userName -> single object, orgDefinedId -> list,
        # externalEmail -> paged result set ({PagingInfo, Items}).
        if result is None:
            return []
        if isinstance(result, dict):
            return result.get("Items", [result])
        return result
