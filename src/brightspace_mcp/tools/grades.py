"""Grades tools (Learning Environment API). Read-only."""

from __future__ import annotations

from mcp.types import ToolAnnotations

from ..context import get_client

_READ_ONLY = ToolAnnotations(readOnlyHint=True)


def register(mcp) -> None:
    @mcp.tool(annotations=_READ_ONLY)
    async def list_grade_objects(org_unit_id: int) -> list[dict]:
        """List all grade items/categories (grade objects) in a course."""
        return await get_client().get("le", f"/{org_unit_id}/grades/")

    @mcp.tool(annotations=_READ_ONLY)
    async def get_grade_object(org_unit_id: int, grade_object_id: int) -> dict:
        """Get a single grade object (item or category) by Id in a course."""
        return await get_client().get(
            "le", f"/{org_unit_id}/grades/{grade_object_id}"
        )

    @mcp.tool(annotations=_READ_ONLY)
    async def get_user_grades(org_unit_id: int, user_id: int) -> list[dict]:
        """Get all grade values for one user in a course (every grade item)."""
        return await get_client().get(
            "le", f"/{org_unit_id}/grades/values/{user_id}/"
        )

    @mcp.tool(annotations=_READ_ONLY)
    async def get_final_grade(org_unit_id: int, user_id: int) -> dict:
        """Get a user's calculated final grade value in a course."""
        return await get_client().get(
            "le", f"/{org_unit_id}/grades/final/values/{user_id}"
        )
