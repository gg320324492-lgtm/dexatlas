"""What the model says about itself.

A docstring that names a value the code never produces is worse than no
docstring: a reader takes it as a promise and looks for the thing that is
missing. These checks hold the model to its own words — the values a field's
documentation names have to be the values the field can actually hold.

The behaviour behind the claims is checked elsewhere: the cross-reference
kinds and the class counts are exercised against real APKs in
``test_first_party_samples.py``, and the storage contract in
``test_storage.py``.
"""

from __future__ import annotations

import ast
import inspect
import re
import textwrap

import pytest
from pydantic import ValidationError

from dexatlas.core.models import (
    InvocationKind,
    MethodReference,
    StringConstant,
)

#: A value written in double backticks, the way this codebase writes code
#: spans in prose.
CODE_SPAN = re.compile(r"``([a-z-]+)``")


def _field_docstring(model: type, field: str) -> str:
    """The prose a field carries, read from the source.

    Pydantic does not collect the string written under a field as the
    field's description — that string is a convention of this codebase, not
    a schema feature — so the source is what has to be read.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(model)))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for index, statement in enumerate(node.body):
            if not isinstance(statement, ast.AnnAssign):
                continue
            target = statement.target
            if not isinstance(target, ast.Name) or target.id != field:
                continue
            following = node.body[index + 1] if index + 1 < len(node.body) else None
            if isinstance(following, ast.Expr) and isinstance(following.value, ast.Constant):
                value = following.value.value
                if isinstance(value, str):
                    return value
    raise AssertionError(f"{model.__name__}.{field} carries no docstring")


# -- the kind of a call ----------------------------------------------------


def test_the_call_kind_docstring_names_exactly_the_kinds_the_index_can_hold() -> None:
    """The docstring and the vocabulary have to be the same list.

    It used to name ``invoke``, ``virtual``, ``direct``, ``interface`` and
    ``dynamic`` while the code produced one value for every row. A reader
    looking for a static call, or a dynamic one, would find neither.
    """
    named = set(CODE_SPAN.findall(_field_docstring(MethodReference, "kind")))

    assert named == {kind.value for kind in InvocationKind}


def test_the_call_kind_vocabulary_is_more_than_one_value() -> None:
    """A vocabulary of one is a constant wearing a vocabulary's clothes."""
    assert len(list(InvocationKind)) > 1


def test_a_call_kind_the_index_cannot_produce_is_refused() -> None:
    """The model has to reject a kind no backend can produce.

    ``dynamic`` was the value the docstring promised. Nothing produces it:
    the Dalvik opcodes that could carry it — ``invoke-custom`` and
    ``invoke-polymorphic`` — name a call site or a method handle, not a
    method, so there is no callee to put in the edge.
    """
    with pytest.raises(ValidationError):
        MethodReference(caller="com.example.A.a()V", callee="com.example.B.b()V", kind="dynamic")


# -- the string constants --------------------------------------------------


def test_the_string_constant_docstring_says_where_the_strings_come_from() -> None:
    """The constants are the DEX string pool, and the docstring has to say so.

    The pool holds type descriptors, member names and source-file names
    beside the text a person wrote, so "a string literal" was never the
    right description of it.
    """
    doc = StringConstant.__doc__ or ""

    assert "pool" in doc.lower()


def test_the_string_constant_docstring_does_not_claim_resources_are_indexed() -> None:
    """Resources are not indexed, and the docstring must not say they are.

    No backend reads the resource table, so a string that exists only in
    ``strings.xml`` is not in the index. The old docstring said "found in the
    DEX or resources", which promised a coverage the tool does not have.
    """
    doc = StringConstant.__doc__ or ""

    assert "or resources" not in doc
