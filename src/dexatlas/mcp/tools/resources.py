"""The tool that finds where a resource is declared.

A resource's *value* and its *place* are different facts. The symbol index
answers "does the APK contain this text?" and "what is ``app_name`` set
to?"; this module answers the question the index cannot — *which file
declares it* — because the declaration is a row of the resource table, with
the file, the qualifier and the position it was read from.

The lookup runs in both directions: by the resource's name
(``app_name`` → ``res/values/strings.xml``) and by its value
(``DexAtlas Demo`` → the same row from the other end). Both directions are
the same read: the rows the resource table holds, filtered by the name or
the value the caller named.
"""

from __future__ import annotations

from dexatlas.core.models import ResourceKind, ResourceString
from dexatlas.core.pipeline import Analyzer
from dexatlas.mcp.errors import RequestError, unknown_project
from dexatlas.mcp.schemas import (
    MAX_LIMIT,
    ResourceDeclarationList,
    ResourceDeclarationView,
)
from dexatlas.mcp.security import bounded_text

#: How much of a resource's value comes back.
#:
#: A values entry is a line and a layout literal is shorter, so the limits
#: are tighter than the ones a source file gets — but the point is the same:
#: nothing comes back unbounded, and the cut is stated in the response.
_RESOURCE_TEXT_LIMITS = {"max_lines": 4, "max_bytes": 2048}

#: The human names of the resource kinds, as the rows spell them.
_KIND_NAMES: dict[ResourceKind, str] = {
    ResourceKind.STRING: "string",
    ResourceKind.STRING_ARRAY: "string_array",
    ResourceKind.PLURAL: "plural",
    ResourceKind.LAYOUT_TEXT: "layout_text",
}


def _require_search_term(*, name: str | None, value: str | None) -> None:
    """Refuse a call that names neither a name nor a value.

    A lookup with no term is not a listing: the resource table of a real APK
    holds hundreds of rows, and a caller that meant "find" has to say what.
    The refusal is a request error, which is the tool's way of saying that
    the *request* was wrong — not that the table was empty.
    """
    if not name and not value:
        raise RequestError(
            "name neither a resource name nor a value to look up",
            code="invalid_arguments",
            detail="pass 'name', 'value', or both",
        )


def find_resource_declarations(
    analyzer: Analyzer,
    project_id: str,
    *,
    name: str | None = None,
    value: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ResourceDeclarationList:
    """Find the declarations of a resource, by its name or by its value.

    The answer is the resource table's own rows: one per declaration, each
    with the file that declares it. Several rows for one name is the normal
    answer — the default declaration and one per language — and the ``file``
    and ``qualifier`` fields are what tell them apart.
    """
    if analyzer.store.get_project(project_id) is None:
        raise unknown_project(project_id)
    _require_search_term(name=name, value=value)

    rows = analyzer.store.list_resources(project_id)
    if name:
        wanted = name.strip()
        rows = [row for row in rows if row.name == wanted]
    if value:
        wanted_value = value.strip()
        rows = [row for row in rows if row.value == wanted_value]

    total = len(rows)
    page = rows[offset : offset + limit]
    return ResourceDeclarationList(
        declarations=[_view(row) for row in page],
        total=total,
        offset=offset,
        limit=min(limit, MAX_LIMIT),
    )


def _view(row: ResourceString) -> ResourceDeclarationView:
    """One declaration, as a reader would want to know it."""
    return ResourceDeclarationView(
        name=row.name,
        value=bounded_text(row.value, **_RESOURCE_TEXT_LIMITS),
        kind=_KIND_NAMES.get(row.kind, str(row.kind)),
        file=row.file,
        qualifier=row.qualifier,
        position=row.position,
        provenance=[entry.locator for entry in row.provenance],
    )
