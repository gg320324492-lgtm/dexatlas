"""What the model says about itself.

A docstring that names a value the code never produces is worse than no
docstring: a reader takes it as a promise and looks for the thing that is
missing. These checks hold the model to its own words — the values a field's
documentation names have to be the values the field can actually hold.

That holds for every field that makes the claim, not for one field: a
documentation that names two or more values is naming a set, and the set has
to be one the code enforces. The fields that name a set are listed below, and
a check says when the list has fallen behind the model.

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
from enum import Enum
from typing import Any, Literal, get_args, get_origin

import pytest
from pydantic import BaseModel, ValidationError

from dexatlas.core import models
from dexatlas.core.models import (
    MANIFEST_COMPONENT_KINDS,
    InvocationKind,
    ManifestComponent,
    MethodReference,
    StringConstant,
)

#: A value written in double backticks, the way this codebase writes code
#: spans in prose.
CODE_SPAN = re.compile(r"``([a-z-]+)``")

#: The fields whose documentation names a closed set of values.
#:
#: Each entry is: the model, the field, the set of values the *documentation*
#: names, the set of values the *implementation* declares, and the other
#: values an instance of the model needs.
#:
#: The two sets are written down separately on purpose. The documented set is
#: the expectation and the implemented set is what the code does; a check that
#: compared one with the other would say nothing when both were wrong in the
#: same way, which is how the manifest component kinds came to describe a set
#: the model did not enforce.
#:
#: A field that is not listed here documents no closed set, so nothing is
#: checked about it. The check below says when a field needs to be listed.
CLOSED_SET_FIELDS: tuple[tuple[Any, str, frozenset[str], frozenset[str], dict[str, Any]], ...] = (
    (
        MethodReference,
        "kind",
        frozenset({"invoke", "virtual", "super", "direct", "static", "interface"}),
        frozenset(kind.value for kind in InvocationKind),
        {"caller": "com.a.Caller.run()V", "callee": "com.a.Callee.run()V"},
    ),
    (
        ManifestComponent,
        "kind",
        frozenset({"activity", "activity-alias", "service", "receiver", "provider", "application"}),
        frozenset(MANIFEST_COMPONENT_KINDS),
        {"name": "com.example.Main"},
    ),
)


def _field_docstring_or_none(model: type, field: str) -> str | None:
    """The prose a field carries, read from the source, or ``None``.

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
    return None


def _field_docstring(model: type, field: str) -> str:
    """The prose a field carries, read from the source."""
    docstring = _field_docstring_or_none(model, field)
    if docstring is None:
        raise AssertionError(f"{model.__name__}.{field} carries no docstring")
    return docstring


def _model_classes() -> list[type[BaseModel]]:
    """Every model the package defines."""
    return [
        obj for obj in vars(models).values() if isinstance(obj, type) and issubclass(obj, BaseModel)
    ]


def _closed_values(annotation: object) -> set[str] | None:
    """The values a field may hold, when its type says which ones."""
    if get_origin(annotation) is Literal:
        return {str(value) for value in get_args(annotation)}
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return {str(member.value) for member in annotation}
    return None


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


# -- every field that names a set of values --------------------------------


def test_the_documented_values_are_the_values_the_field_can_hold() -> None:
    """The prose and the code have to name the same set.

    A field whose documentation lists the values it holds is making a promise
    about what the code accepts. The promise has to be kept in both
    directions: a value the field refuses must not be in the list, and a
    value in the list must not be refused.
    """
    problems: list[str] = []
    for model, field, documented_set, _, _ in CLOSED_SET_FIELDS:
        documented = set(CODE_SPAN.findall(_field_docstring(model, field)))
        if documented != documented_set:
            problems.append(
                f"{model.__name__}.{field}: the documentation names "
                f"{sorted(documented)}, the field holds {sorted(documented_set)}"
            )

    assert not problems, "the documentation and the field disagree:\n" + "\n".join(problems)


def test_the_implementation_declares_the_values_the_documentation_names() -> None:
    """The set the code enforces has to be the set the prose names.

    The documented set and the implemented set are written down separately,
    so this is a comparison and not an identity: a kind added to the
    implementation but not to the documentation is a value the model accepts
    and the reader was never told about.
    """
    problems: list[str] = []
    for model, field, documented_set, implemented, _ in CLOSED_SET_FIELDS:
        if set(implemented) != documented_set:
            problems.append(
                f"{model.__name__}.{field}: the documentation names "
                f"{sorted(documented_set)}, the implementation declares {sorted(implemented)}"
            )

    assert not problems, "the documentation and the implementation disagree:\n" + "\n".join(
        problems
    )


def test_a_field_that_names_a_set_of_values_is_one_of_the_checked_fields() -> None:
    """The list of checked fields has to cover the fields that need checking.

    A documentation that names two or more values is naming a set of values.
    The set is only checked when the field is in the list above, so a field
    added to the model with such a documentation and left out of the list
    would be a promise nobody watches — which is how the manifest component
    kinds came to describe a set the model did not enforce.
    """
    checked = {(model, field) for model, field, _, _, _ in CLOSED_SET_FIELDS}
    unchecked: list[str] = []
    for model in _model_classes():
        for field in model.model_fields:
            documented = set(CODE_SPAN.findall(_field_docstring_or_none(model, field) or ""))
            # One code span is an example of a value; two or more are a set.
            if len(documented) >= 2 and (model, field) not in checked:
                unchecked.append(f"{model.__name__}.{field} names {sorted(documented)}")

    assert not unchecked, "fields that name a set of values and are not checked:\n" + "\n".join(
        unchecked
    )


def test_a_field_holds_every_value_it_declares() -> None:
    """A documented value the field refuses is a promise the code breaks."""
    for model, field, documented_set, _, extra in CLOSED_SET_FIELDS:
        for value in sorted(documented_set):
            instance = model(**extra, **{field: value})
            assert getattr(instance, field) == value


def test_a_field_refuses_a_value_it_does_not_declare() -> None:
    """The set has to be enforced, not only described.

    A field that holds any string can be given any string, so a documented
    set is a description and not a contract. The manifest component kinds
    were the case in point: the documentation named five tags and the model
    accepted every one.
    """
    for model, field, _, _, extra in CLOSED_SET_FIELDS:
        with pytest.raises(ValidationError):
            model(**extra, **{field: "not-a-declared-value"})


def test_a_field_with_an_enumerated_type_holds_exactly_that_type() -> None:
    """An enum is a set of values the model enforces on its own.

    This is the automatic half of the check: a field whose type is an
    enumeration cannot hold a value outside it, whatever the documentation
    says about it.
    """
    for model in _model_classes():
        for field, info in model.model_fields.items():
            closed = _closed_values(info.annotation)
            if closed is None:
                continue
            documented = set(CODE_SPAN.findall(_field_docstring_or_none(model, field) or ""))
            if not documented:
                continue
            assert documented == closed, (
                f"{model.__name__}.{field} documents {sorted(documented)} "
                f"but its type holds {sorted(closed)}"
            )
