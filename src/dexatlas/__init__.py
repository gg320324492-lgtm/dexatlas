"""DexAtlas — evidence-first Android analysis platform."""

from __future__ import annotations

#: The single source of truth for the version. ``pyproject.toml`` reads it through
#: hatchling's version hook, so the package metadata and the running code cannot
#: disagree — which they did, when the number was written in both places.
#:
#: The ``.devN`` suffix is added to a tree that is ahead of the last release, and
#: dropped when the release is cut.
__version__ = "0.1.3"

__all__ = ["__version__"]
