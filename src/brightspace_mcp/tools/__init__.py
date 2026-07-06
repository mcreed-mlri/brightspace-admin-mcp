"""Tool modules. Each exposes register(mcp) to attach its tools to the FastMCP server.

Feature flags (read via config.flag so env access stays in one place):
- BRIGHTSPACE_ENABLE_RAW=1     opt IN to the raw api_get escape hatch (default off,
                               so the default install exposes only curated endpoints)
- BRIGHTSPACE_ENABLE_DATAHUB=0 opt OUT of bulk Data Hub exports (default on)
"""

from ..config import flag
from . import datahub, enrollments, grades, orgunits, raw, users

ALL_MODULES = [users, orgunits, enrollments, grades, raw]


def register_all(mcp) -> None:
    for module in ALL_MODULES:
        module.register(mcp)
    if flag("BRIGHTSPACE_ENABLE_DATAHUB", default=True):
        datahub.register(mcp)
    if flag("BRIGHTSPACE_ENABLE_RAW", default=False):
        raw.register_raw(mcp)
