"""Org structure tools: organization, org units, course offerings, semesters."""

from __future__ import annotations

from ..context import get_client


def register(mcp) -> None:
    @mcp.tool()
    async def get_organization() -> dict:
        """Get top-level info about this Brightspace organization (name, timezone, Id)."""
        return await get_client().get("lp", "/organization/info")

    @mcp.tool()
    async def search_orgunits(
        org_unit_type: str | None = None,
        name: str | None = None,
        code: str | None = None,
        exact_org_unit_code: str | None = None,
    ) -> list[dict]:
        """Search org units (courses, departments, semesters, etc.).

        Filters (all optional): org_unit_type (e.g. 'Course Offering', 'Department',
        'Semester'), name (partial match), code (partial match), exact_org_unit_code.
        Returns all matching org units (paging followed automatically).
        """
        params: dict = {}
        if org_unit_type:
            params["orgUnitType"] = org_unit_type
        if name:
            params["orgUnitName"] = name
        if code:
            params["orgUnitCode"] = code
        if exact_org_unit_code:
            params["exactOrgUnitCode"] = exact_org_unit_code
        return await get_client().get_paged("lp", "/orgstructure/", params=params)

    @mcp.tool()
    async def get_orgunit(org_unit_id: int) -> dict:
        """Get properties of a single org unit by its OrgUnitId."""
        return await get_client().get("lp", f"/orgstructure/{org_unit_id}")

    @mcp.tool()
    async def get_descendants(org_unit_id: int) -> list[dict]:
        """List all descendant org units beneath the given org unit."""
        return await get_client().get_paged(
            "lp", f"/orgstructure/{org_unit_id}/descendants/paged/"
        )

    @mcp.tool()
    async def list_orgunit_types() -> list[dict]:
        """List the org unit types defined in this instance (with their Id and name)."""
        return await get_client().get("lp", "/outypes/")
