"""The read-only MCP server over a DexAtlas workspace.

The server exposes the analysis an agent needs — the projects, their
symbols, the call sites between their methods, the evidence records and the
places those records were read from — and nothing else. It reads; it never
writes, it never runs a shell, and it never hands back more than a bounded
amount of anything.

The tools are registered in :mod:`dexatlas.mcp.server`, and the work they
do is in :mod:`dexatlas.mcp.tools`.
"""

from dexatlas.mcp.schemas import DATA_NOTICE

__all__ = ["DATA_NOTICE"]
