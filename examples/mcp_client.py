"""A client that talks to the DexAtlas MCP server.

It starts the server as a subprocess over stdio, asks it what it can do, and
asks it for the projects in the workspace:

    uv run --no-sync python examples/mcp_client.py

It needs **no model provider**. The server is a tool server, and a client
that only calls tools needs nothing else — which is the point of the
separation the milestone draws between a tool server and an agent.

Point it at a workspace with ``DEXATLAS_WORKSPACE``, the same way the rest
of DexAtlas is pointed at one.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

from mcp.client import Client
from mcp.client.stdio import StdioServerParameters


async def ask() -> int:
    """Start the server, look at it, and ask it something."""
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "dexatlas.mcp.server"],
        env=dict(os.environ),
    )

    async with Client(parameters) as client:
        listed = await client.list_tools()
        tools = listed.tools
        print(f"the server offers {len(tools)} tools:")
        for tool in tools:
            first = (tool.description or "").splitlines()[0]
            print(f"  {tool.name:20} {first}")

        projects = await client.call_tool("list_projects", {"limit": 5})
        payload = projects.structured_content or {}
        print("\nthe projects in the workspace:")
        for project in payload.get("projects", []):
            print(
                f"  {project['id']:22} {project['status']:10} "
                f"{project['call_site_count']:>4} call sites, "
                f"{project['call_edge_count']:>3} call edges"
            )
        if not payload.get("projects"):
            print("  (none — analyse an APK first, or point DEXATLAS_WORKSPACE elsewhere)")
        print(json.dumps(payload.get("projects", [])[:1], indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(ask()))
