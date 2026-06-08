"""Enrollment tools: who is enrolled where, and classlists."""

from __future__ import annotations

from ..context import get_client


def register(mcp) -> None:
    @mcp.tool()
    async def list_user_enrollments(user_id: int) -> list[dict]:
        """List all org units a given user is enrolled in (with their role in each)."""
        return await get_client().get_paged(
            "lp", f"/enrollments/users/{user_id}/orgUnits/"
        )

    @mcp.tool()
    async def list_orgunit_enrollments(
        org_unit_id: int, role_id: int | None = None
    ) -> list[dict]:
        """List users enrolled in an org unit, optionally filtered to a single RoleId."""
        params = {"roleId": role_id} if role_id is not None else None
        return await get_client().get_paged(
            "lp", f"/enrollments/orgUnits/{org_unit_id}/users/", params=params
        )

    @mcp.tool()
    async def get_classlist(org_unit_id: int) -> list[dict]:
        """Get the classlist (enrolled people + emails) for a course offering.

        Uses the Learning Environment API; org_unit_id must be a course offering.
        """
        return await get_client().get("le", f"/{org_unit_id}/classlist/")

    @mcp.tool()
    async def get_user_enrollment(org_unit_id: int, user_id: int) -> dict:
        """Get a single user's enrollment record in one org unit (role, status, dates)."""
        return await get_client().get(
            "lp", f"/enrollments/orgUnits/{org_unit_id}/users/{user_id}"
        )
