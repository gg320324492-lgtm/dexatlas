"""DexAtlas — evidence-first Android analysis platform."""

from __future__ import annotations

#: The single source of truth for the version. ``pyproject.toml`` reads it through
#: hatchling's version hook, so the package metadata and the running code cannot
#: disagree — which they did, when the number was written in both places.
#:
#: The ``.dev0`` suffix marks a tree that is ahead of the last release: v0.1.2 is
#: published, and this branch carries fixes that are not in it yet. The suffix is
#: dropped when the next release is cut.
__version__ = "0.1.3.dev0"

__all__ = ["__version__"]
