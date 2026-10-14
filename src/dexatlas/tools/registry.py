"""Backend discovery.

A missing backend is a normal state, not an error condition. DexAtlas reports what it can
do with what is installed and records what it could not do, so a partial analysis is
still a useful analysis.
"""

from __future__ import annotations

from collections.abc import Sequence

from dexatlas.config.settings import Settings
from dexatlas.tools.androguard.adapter import AndroguardBackend
from dexatlas.tools.apktool.adapter import ApktoolBackend
from dexatlas.tools.base import Backend
from dexatlas.tools.jadx.adapter import JadxBackend


def default_backends(settings: Settings) -> list[Backend]:
    return [JadxBackend(settings), ApktoolBackend(settings), AndroguardBackend(settings)]


class BackendRegistry:
    """Holds the configured analysis backends."""

    def __init__(self, settings: Settings, backends: Sequence[Backend] | None = None) -> None:
        self._settings = settings
        self._backends: dict[str, Backend] = {
            backend.name: backend
            for backend in (backends if backends is not None else default_backends(settings))
        }

    def get(self, name: str) -> Backend:
        try:
            return self._backends[name]
        except KeyError:
            known = ", ".join(sorted(self._backends))
            raise KeyError(f"unknown backend {name!r}; available: {known}") from None

    def all(self) -> Sequence[Backend]:
        return tuple(self._backends.values())

    def available(self) -> Sequence[Backend]:
        return tuple(b for b in self._backends.values() if b.available())

    def missing(self) -> Sequence[Backend]:
        return tuple(b for b in self._backends.values() if not b.available())

    def versions(self) -> dict[str, str | None]:
        return {backend.name: backend.version() for backend in self._backends.values()}


__all__ = ["BackendRegistry"]
