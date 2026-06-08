"""Tool modules. Each exposes register(mcp) to attach its tools to the FastMCP server."""

from . import datahub, enrollments, grades, orgunits, raw, users

ALL_MODULES = [users, orgunits, enrollments, grades, datahub, raw]


def register_all(mcp) -> None:
    for module in ALL_MODULES:
        module.register(mcp)
