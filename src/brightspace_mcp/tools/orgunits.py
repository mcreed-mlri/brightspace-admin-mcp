"""Org structure tools: organization, org units, course offerings, semesters."""

from __future__ import annotations

from mcp.types import ToolAnnotations

from ..client import DEFAULT_MAX_ITEMS
from ..context import get_client

_READ_ONLY = ToolAnnotations(readOnlyHint=True)


def register(mcp) -> None:
    @mcp.tool(annotations=_READ_ONLY)
    async def get_organization() -> dict:
        """Get top-level info about this Brightspace organization (name, timezone, Id)."""
        return await get_client().get("lp", "/organization/info")

    @mcp.tool(annotations=_READ_ONLY)
    async def search_orgunits(
        org_unit_type: str | None = None,
        name: str | None = None,
        code: str | None = None,
        exact_org_unit_code: str | None = None,
        max_items: int = DEFAULT_MAX_ITEMS,
    ) -> dict:
        """Search org units (courses, departments, semesters, etc.).

        Filters (all optional): org_unit_type (e.g. 'Course Offering', 'Department',
        'Semester'), name (partial match), code (partial match), exact_org_unit_code.
        Returns {items, count, truncated}; truncated=true means more matches exist —
        narrow the search or raise max_items.
        """
        params: dict = {}
        if org_unit_type:
            if org_unit_type.isdigit():
                params["orgUnitType"] = int(org_unit_type)
            else:
                types = await get_client().get("lp", "/outypes/") or []
                match = next(
                    (t for t in types if t.get("Name", "").lower() == org_unit_type.lower()),
                    None,
                )
                if not match:
                    available = [t.get("Name") for t in types]
                    raise ValueError(f"Unknown org unit type '{org_unit_type}'. Available: {available}")
                params["orgUnitType"] = match["Id"]
        if name:
            params["orgUnitName"] = name
        if code:
            params["orgUnitCode"] = code
        if exact_org_unit_code:
            params["exactOrgUnitCode"] = exact_org_unit_code
        return await get_client().get_paged(
            "lp", "/orgstructure/", params=params, max_items=max_items
        )

    @mcp.tool(annotations=_READ_ONLY)
    async def get_orgunit(org_unit_id: int) -> dict:
        """Get properties of a single org unit by its OrgUnitId."""
        return await get_client().get("lp", f"/orgstructure/{org_unit_id}")

    @mcp.tool(annotations=_READ_ONLY)
    async def get_descendants(
        org_unit_id: int, max_items: int = DEFAULT_MAX_ITEMS
    ) -> dict:
        """List descendant org units beneath the given org unit.

        Returns {items, count, truncated}.
        """
        return await get_client().get_paged(
            "lp", f"/orgstructure/{org_unit_id}/descendants/paged/", max_items=max_items
        )

    @mcp.tool(annotations=_READ_ONLY)
    async def list_orgunit_types() -> list[dict]:
        """List the org unit types defined in this instance (with their Id and name)."""
        return await get_client().get("lp", "/outypes/")
