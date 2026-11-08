"""The errors the MCP server answers with.

A request the server cannot answer is not a crash and not an empty result:
it is a request that was wrong, and the caller has to be able to tell it
from "there is nothing there". So the error says which it is.
"""

from __future__ import annotations

from typing import Any


class RequestError(Exception):
    """A request the server cannot answer as it was asked.

    The code is a short word a caller can branch on, and the detail says
    what was wrong in terms it can act on.
    """

    def __init__(self, message: str, *, code: str, **detail: Any) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.detail = detail

    def as_dict(self) -> dict[str, Any]:
        """The error as a caller can read it."""
        return {"code": self.code, "message": self.message, "detail": self.detail}


def unknown_project(project_id: str) -> RequestError:
    """The workspace holds no project by that name."""
    return RequestError(
        f"this workspace holds no project {project_id!r}",
        code="unknown_project",
        project_id=project_id,
    )


def unknown_method(method_id: str) -> RequestError:
    """The method id is not one this project can answer about."""
    return RequestError(
        f"{method_id!r} is not a method id: it looks like com.example.Class.method(Ljava/lang/String;)V",
        code="unknown_method",
        method_id=method_id,
    )


__all__ = ["RequestError", "unknown_method", "unknown_project"]
