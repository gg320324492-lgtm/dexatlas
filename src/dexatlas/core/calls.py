"""Call sites and call edges — the two different things a cross-reference is.

A **call site** is one place in the bytecode: the DEX file it was read out of,
the method that made the call, the instruction offset inside that method, the
opcode that carried the call, and the method that was called. A **call edge**
is the relationship between two methods, aggregated over the call sites that
make it.

The two are not the same thing, and a count that does not say which of the two
it counts is a number nobody can check:

* one method that calls the same target twice is **one edge and two call
  sites** -- the sites differ in the instruction offset;
* one method defined in two DEX files is **one edge and two call sites** as
  well -- the sites differ in the DEX file rather than in the offset.

The edge is derived from the sites, never the other way round. An edge that
exists without sites has nothing behind it, and the sites are what a citation
points at.

The two kinds of duplication need different treatment, and a design that only
handles one of them is the bug this module exists to fix. A table keyed on the
caller and the callee alone collapses the first kind -- the two offsets become
one row, and the call sites cannot be recovered from it. A table keyed on the
caller, the callee and the offset alone collapses the second kind -- the two
DEX files become one row, and the provenance that says which file the call was
read out of is lost. The key here carries both: the DEX file *and* the offset.
"""

from __future__ import annotations

from collections.abc import Iterable

from dexatlas.core.models import InvocationKind, MethodReference, Provenance

#: The instruction offset of a call site whose position is not known.
#:
#: A call that did not come out of bytecode names no instruction, and it is
#: recorded as -1 rather than as 0: 0 is a real offset, the first instruction
#: of a method, and a caller that cannot tell the two apart is looking at a
#: number that points somewhere it never went.
UNKNOWN_OFFSET = -1


class CallSite(MethodReference):
    """One concrete call location: a place in the bytecode where a call happens.

    A reference says that a caller invokes a callee. A call site says *where*:
    which DEX file the instruction was read out of, and where in the caller's
    bytecode it sits. Two calls from the same method to the same target are
    two call sites when they sit at different offsets, and one call site when
    they do not.
    """

    dex_name: str = ""
    """The DEX file the instruction was read out of.

    Empty when the call did not come out of a DEX file. A method defined in
    two DEX files is one method with two copies of its body, and each copy
    holds its own call sites: the same method calling the same target from
    two different bytes. Their citations differ too, because the citation
    names the file.
    """

    instruction_offset: int = UNKNOWN_OFFSET
    """Where in the caller's bytecode the call instruction sits.

    The offset is in bytes, counted from the first instruction of the method.
    It is what tells two calls from the same method to the same target apart,
    and it is the reason the index can hold both of them.
    """


class CallEdge(MethodReference):
    """The aggregated relationship between two methods.

    An edge is the caller, the callee and the way the call is made. It is
    derived from the call sites that make it up, and it says how many of them
    there were: an edge with three call sites is one relationship that three
    places in the bytecode make.
    """

    site_count: int = 0
    """How many call sites this edge is made of."""


def as_call_site(reference: MethodReference) -> CallSite:
    """The call site a reference describes.

    A reference that did not come out of bytecode names no DEX file and no
    instruction, and this says so rather than inventing one: an offset that
    was never read points a reader at an instruction that does not exist.
    """
    if isinstance(reference, CallSite):
        return reference
    return CallSite(
        caller=reference.caller,
        callee=reference.callee,
        kind=reference.kind,
        provenance=reference.provenance,
    )


def derive_edges(sites: Iterable[CallSite]) -> list[CallEdge]:
    """The edges the call sites describe.

    An edge is the caller, the callee and the opcode that carried the call, so
    two calls from the same method to the same target with the same opcode are
    one edge however many places in the bytecode they sit at. The opcode is
    part of the relationship because a static call and a virtual call between
    the same two methods are two different relationships.

    The edges come out in a fixed order -- by caller, then callee, then kind --
    so that two runs over the same APK produce the same list and the same
    evidence ids.
    """
    grouped: dict[tuple[str, str, InvocationKind], list[CallSite]] = {}
    for site in sorted(sites, key=_site_order):
        grouped.setdefault((site.caller, site.callee, site.kind), []).append(site)
    edges = [
        CallEdge(
            caller=caller,
            callee=callee,
            kind=kind,
            site_count=len(group),
            provenance=merged_provenance(group),
        )
        for (caller, callee, kind), group in grouped.items()
    ]
    edges.sort(key=lambda edge: (edge.caller, edge.callee, edge.kind.value))
    return edges


def merged_provenance(sites: Iterable[CallSite]) -> list[Provenance]:
    """The citations of a group of call sites, one per distinct place.

    The same locator is kept once, because the same call read twice is one
    place; a locator that names another DEX file is a different place, and is
    kept. The order follows the sites, so the merged list is the same on every
    run.
    """
    by_locator: dict[str, Provenance] = {}
    for site in sites:
        for provenance in site.provenance:
            by_locator.setdefault(provenance.locator, provenance)
    return list(by_locator.values())


def _site_order(site: CallSite) -> tuple[str, str, str, str, int]:
    """The order call sites are read in: a fixed one, so the output is stable."""
    return (
        site.caller,
        site.callee,
        site.kind.value,
        site.dex_name,
        site.instruction_offset,
    )


__all__ = [
    "UNKNOWN_OFFSET",
    "CallEdge",
    "CallSite",
    "as_call_site",
    "derive_edges",
    "merged_provenance",
]
