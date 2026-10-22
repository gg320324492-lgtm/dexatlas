"""Which method a request means.

A name is not a method. ``sign`` can be three different methods, and only the DEX
descriptor tells them apart: ``(Ljava/lang/String;)V``,
``(Ljava/lang/String;Ljava/lang/String;)V`` and ``()V`` are three methods that
share one name. The symbol index already stores that descriptor, so the information
needed to choose is in the workspace — it was simply never asked for.

Two vocabularies live here. The first is the choice itself: the candidate a name
could have meant, and the error raised when a name means more than one of them. The
second is the translation between the two spellings of a method — the DEX
descriptor, which names every type in full, and the decompiled signature, which
names a type by its bare name and leaves the imports to say which class that is.
Neither spelling is a subset of the other, and a method is only the same method in
both when the translation says so.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from pydantic import BaseModel

#: What a DEX descriptor looks like: an argument list in brackets, and a return type.
#:
#: A string that does not have this shape is not a descriptor, and saying so is
#: better than treating it as one: ``(Ljava/lang/String;`` would otherwise be
#: read as a method that takes no arguments and returns nothing.
DESCRIPTOR_SHAPE = re.compile(r"^\(.*\).+$")

#: Java's primitive types, and the letter each has in a DEX descriptor.
PRIMITIVE_TYPES: dict[str, str] = {
    "boolean": "Z",
    "byte": "B",
    "char": "C",
    "short": "S",
    "int": "I",
    "long": "J",
    "float": "F",
    "double": "D",
}

#: The same table read the other way: a descriptor letter, and the name it spells.
PRIMITIVE_LETTERS: dict[str, str] = {letter: name for name, letter in PRIMITIVE_TYPES.items()}

#: A Java type as source writes it: a name, and the dots between its parts.
JAVA_TYPE_NAME = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*(\.[A-Za-z_$][A-Za-z0-9_$]*)*$")

#: The names a decompiler writes when it could not work out what a parameter is.
OPAQUE_TYPE_NAME = re.compile(r"^(?:var|arg)\d+$")

#: The rank of a parameter whose type the decompiler could not work out.
#:
#: Such a parameter is compatible with any type, so it never decides between two
#: overloads — it only keeps them both in the running. The number is worse than
#: any rank a type the source spelled out can have.
UNKNOWN_RANK = 1000


class MethodCandidate(BaseModel):
    """A method that a request for a method name could have meant.

    Two overloads are one name and two descriptors, so the descriptor is what
    tells them apart — and it is what a caller has to send to get one of them.
    """

    name: str
    """The DEX method name: ``sign``, or ``<init>`` for a constructor."""

    descriptor: str | None = None
    """The DEX descriptor, when it is known.

    It is ``None`` when the symbol index does not hold the method — the index is
    built by a backend that may not have run — and the decompiled source does
    not say which package a type came from, so it cannot supply one.
    """

    signature: str
    """How the candidate is written, for a message a reader reads.

    The DEX spelling when the descriptor is known, the Java spelling when it is
    not.
    """


class AmbiguousMethodError(Exception):
    """A method name that matches more than one method.

    Raised instead of returning a body, because the body of the wrong overload is
    worse than no body at all: it reads like evidence, and an agent that quotes it
    quotes the wrong method.
    """

    def __init__(
        self,
        class_name: str,
        method_name: str,
        candidates: Sequence[MethodCandidate],
    ) -> None:
        self.class_name = class_name
        """The class the request was about."""

        self.method_name = method_name
        """The name that matched more than one method."""

        self.candidates = list(candidates)
        """Every method the name matched."""

        super().__init__(self.describe())

    def describe(self) -> str:
        """The one-line reason, for a log or for the message a caller reads."""
        spellings = ", ".join(candidate.signature for candidate in self.candidates)
        return (
            f"{self.method_name} names {len(self.candidates)} methods of "
            f"{self.class_name} ({spellings}); a descriptor is needed to choose one"
        )


def is_descriptor(text: str) -> bool:
    """Whether a string has the shape of a DEX descriptor.

    A request that carries something else is a wrong request, and saying so is
    different from saying that the method has no source: the first is fixed by
    changing the request, the second is not.
    """
    return DESCRIPTOR_SHAPE.match(text.strip()) is not None


def simple_class_name(class_name: str) -> str:
    """The bare name of a class, without its package or its outer class.

    ``com.example.Outer$Helper`` is ``Helper``. A constructor is written under
    the class's own name in Java, so this is what a DEX ``<init>`` is filed
    under when a caller asks for a method by name.
    """
    return class_name.rpartition(".")[2].rpartition("$")[2]


def dex_class_name(dotted: str) -> str:
    """A class name in the form a DEX descriptor uses: slashes, not dots.

    ``com.example.Foo`` is ``com/example/Foo``.
    """
    return dotted.replace(".", "/")


def descriptor_arguments(descriptor: str) -> list[str] | None:
    """The argument types of a descriptor, read off one at a time.

    A descriptor packs its argument types together — ``(Ljava/lang/String;I)V``
    — so they have to be read off one at a time: a class type runs to its
    terminating semicolon, and every ``[`` in front of one is another dimension
    of an array.

    The answer is ``None`` when the text is not a descriptor at all, so that a
    caller can tell "takes no arguments" from "is not a descriptor".
    """
    open_paren = descriptor.find("(")
    close_paren = descriptor.find(")", open_paren + 1)
    if open_paren == -1 or close_paren == -1:
        return None
    return _split_descriptor_types(descriptor[open_paren + 1 : close_paren])


def _split_descriptor_types(text: str) -> list[str]:
    """The individual types in a run of packed descriptor types."""
    types: list[str] = []
    index = 0
    while index < len(text):
        start = index
        while index < len(text) and text[index] == "[":
            index += 1
        if index >= len(text):
            break
        if text[index] == "L":
            end = text.find(";", index)
            if end == -1:
                break
            index = end + 1
        else:
            index += 1
        types.append(text[start:index])
    return types


@dataclass(frozen=True, slots=True)
class JavaType:
    """A parameter type as the decompiled source spells it."""

    name: str
    """The type's name, without its generics and without its array brackets."""

    dimensions: int
    """How many dimensions of array the type is."""

    known: bool
    """Whether the source said what the type is at all.

    A decompiler that could not work out a parameter's type writes ``var1``,
    and ``var1`` says nothing about which class the parameter is.
    """


@dataclass(frozen=True, slots=True)
class JavaContext:
    """What a decompiled file says about the names it uses.

    A Java source spells a type by a simple name and leaves the imports, the
    package and the file's own classes to say which class that name is. A DEX
    descriptor names every type in full. This is the evidence that turns the
    one into the other, and it is per file: the same simple name means different
    classes in two files.
    """

    package: str = ""
    """The package the file declares, dotted. Empty when it declares none."""

    imports: Mapping[str, str] = field(default_factory=dict)
    """Single-type imports: the simple name a source uses, and the class it names."""

    star_imports: tuple[str, ...] = ()
    """The packages a source imports everything from."""

    own_classes: Mapping[str, str] = field(default_factory=dict)
    """The classes the file itself declares: the simple name, and the DEX name."""

    def class_named(self, simple_name: str, dotted: str) -> str | None:
        """The DEX name of a class a source names by a path, when it is known.

        ``dotted`` is the path the source wrote, and ``simple_name`` its last
        part. The path may be the whole name of a class in another package, or
        only the outer class of a nested one.
        """
        imported = self.imports.get(simple_name)
        if imported is not None and (dotted == simple_name or imported == dotted):
            return dex_class_name(imported)
        own = self.own_classes.get(simple_name)
        if own is not None and (dotted == simple_name or dex_class_name(dotted) == own):
            return own
        return None


def parse_parameter_types(text: str) -> tuple[str, ...]:
    """The types of a method's parameters, in order.

    The source writes a type and a name — ``String key`` — but the type is what
    identifies the method and the name is not always there. Splitting on commas
    has to respect the angle brackets of a generic type, and the type of a
    parameter is everything except a trailing identifier.
    """
    types: list[str] = []
    for part in _split_parameters(text):
        words = [word for word in _split_words(part) if not word.startswith("@")]
        if words and words[0] == "final":
            words = words[1:]
        if not words:
            continue
        types.append(" ".join(words[:-1]) if len(words) > 1 else words[0])
    return tuple(types)


def parse_java_type(text: str) -> JavaType:
    """The type a parameter declaration names.

    ``String`` is one type; ``String[]`` is an array of it; ``String...`` is the
    same array written the way a varargs parameter is written; and
    ``List<String>`` is a ``List`` — the generics say nothing about which class
    the descriptor will name.
    """
    raw = text.strip()
    dimensions = 0
    if raw.endswith("..."):
        raw = raw[:-3].strip()
        dimensions += 1
    while raw.endswith("[]"):
        raw = raw[:-2].strip()
        dimensions += 1
    name = _strip_generics(raw)
    known = bool(JAVA_TYPE_NAME.match(name)) and not OPAQUE_TYPE_NAME.match(name)
    return JavaType(name=name, dimensions=dimensions, known=known)


def type_candidates(name: str, context: JavaContext) -> list[str]:
    """The DEX class names a type name could name, the most precise first.

    The order is the order Java itself resolves a simple name in: the file's own
    classes, then a single-type import, then the file's own package, then the
    packages imported wholesale, and ``java.lang`` last. The position in the
    list is the measure of how much the source said: the first reading is the
    one Java would have used, and a later one is a reading the source did not
    rule out but did not choose either.
    """
    if "." in name:
        return _qualified_candidates(name, context)

    candidates: list[str] = []
    own = context.own_classes.get(name)
    if own is not None:
        candidates.append(own)
    imported = context.imports.get(name)
    if imported is not None:
        candidates.append(dex_class_name(imported))
    if context.package:
        candidates.append(dex_class_name(context.package) + "/" + name)
    for star in context.star_imports:
        candidates.append(dex_class_name(star) + "/" + name)
    candidates.append("java/lang/" + name)
    return candidates


def _qualified_candidates(name: str, context: JavaContext) -> list[str]:
    """The DEX class names a qualified type name could name.

    A qualified name is either a class in another package, or a nested class
    reached through its outer one — and the source does not always say which,
    because ``com.foo.Outer.Inner`` is a class ``Inner`` in the package
    ``com.foo.Outer`` as well as a nested class ``Outer$Inner`` in ``com.foo``.
    Every reading is listed, most likely first.
    """
    parts = name.split(".")
    candidates: list[str] = []

    # A prefix the source names as a class decides the reading. Java resolves
    # the leftmost part first: if it is a type, the rest is a member of it,
    # and if it is not, it is a package.
    for count in range(1, len(parts)):
        known = context.class_named(parts[count - 1], ".".join(parts[:count]))
        if known is not None:
            candidates.append(known + "$" + "$".join(parts[count:]))
            break

    # Otherwise the name is a package path, and where the package ends and the
    # class begins is not written down. The last segment is the class itself
    # in the most ordinary reading, so that one comes first.
    for split in range(len(parts) - 1, 0, -1):
        candidates.append("/".join(parts[:split]) + "/" + "$".join(parts[split:]))
    return candidates


def match_type_rank(java_type: JavaType, descriptor_type: str, context: JavaContext) -> int | None:
    """How precisely a Java type can be the type a descriptor type names.

    ``None`` — it cannot be that type at all: the shapes do not agree, or the
    source says a different class.

    ``0`` — it is that type, and the source said so outright.

    A larger number — the source could be naming that type, but it did not say
    so on its own; the number says how far down the list of readings the answer
    was found. A decompiler that could not work out the type at all ranks
    :data:`UNKNOWN_RANK`, because it decides nothing.
    """
    if not java_type.known:
        return UNKNOWN_RANK

    dex_type, dimensions = _split_descriptor_type(descriptor_type)
    if java_type.dimensions != dimensions:
        return None

    if dex_type in PRIMITIVE_LETTERS:
        if java_type.name not in PRIMITIVE_TYPES:
            return None
        return 0 if PRIMITIVE_TYPES[java_type.name] == dex_type else None

    if java_type.name in PRIMITIVE_TYPES:
        # The source says a primitive and the descriptor says a class.
        return None

    for index, candidate in enumerate(type_candidates(java_type.name, context)):
        if candidate == dex_type:
            return index
    return None


def match_parameter_rank(
    parameters: Sequence[str], descriptor: str, context: JavaContext
) -> int | None:
    """How precisely a decompiled parameter list matches a descriptor.

    The rank is the least certain parameter: a list that spells one type
    exactly and another one only possibly is no more certain than the uncertain
    one, because the uncertain one is the one that could belong to a different
    method.
    """
    arguments = descriptor_arguments(descriptor)
    if arguments is None:
        return None
    if len(parameters) != len(arguments):
        return None
    rank = 0
    for text, argument in zip(parameters, arguments, strict=True):
        one = match_type_rank(parse_java_type(text), argument, context)
        if one is None:
            return None
        rank = max(rank, one)
    return rank


def _split_descriptor_type(descriptor_type: str) -> tuple[str, int]:
    """A descriptor type without its array brackets, and how many there were."""
    dimensions = 0
    while descriptor_type.startswith("["):
        dimensions += 1
        descriptor_type = descriptor_type[1:]
    if descriptor_type.startswith("L") and descriptor_type.endswith(";"):
        descriptor_type = descriptor_type[1:-1]
    return descriptor_type, dimensions


def _strip_generics(text: str) -> str:
    """The type without its generic arguments."""
    if "<" not in text:
        return text.strip()
    depth = 0
    kept: list[str] = []
    for char in text:
        if char == "<":
            depth += 1
        elif char == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            kept.append(char)
    return "".join(kept).strip()


def _split_parameters(text: str) -> list[str]:
    """The parts of a parameter list, split on the commas outside the brackets."""
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in text:
        if char == "<":
            depth += 1
        elif char == ">":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    parts.append("".join(current))
    return parts


def _split_words(text: str) -> list[str]:
    """The words of a parameter declaration, split on the spaces outside the brackets."""
    words: list[str] = []
    current: list[str] = []
    depth = 0
    for char in text:
        if char == "<":
            depth += 1
        elif char == ">":
            depth = max(0, depth - 1)
        if depth == 0 and char.isspace():
            if current:
                words.append("".join(current))
                current = []
            continue
        current.append(char)
    if current:
        words.append("".join(current))
    return words
