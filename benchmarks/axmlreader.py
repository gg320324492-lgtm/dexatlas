"""A reader for Android's binary XML, and for the manifest inside an APK.

Deliberately independent of the tool under measurement, for the same reason as
:mod:`benchmarks.dexreader`: a benchmark whose expectations are checked with
the tool it measures cannot catch the tool being wrong. This module reads the
bytes of ``AndroidManifest.xml`` straight out of an APK zip and decodes the
binary format directly (format spec: the AOSP ``ResourceTypes.cpp``).

What it decodes is what a manifest question is about:

* the element names, in document order;
* every attribute, with its namespace and its value — a string from the pool,
  an integer, or a boolean.

It exists here because of a concrete finding: in four of the five first-party
samples the checked-in ``AndroidManifest.xml`` and the manifest inside the APK
disagree about ``minSdkVersion``. The APK is what the analysis reads and what
the report describes, so the APK is what the benchmark's expectations are
written against — and this reader is how that claim is checked without asking
the tool under test.
"""

from __future__ import annotations

import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path

#: Chunk types of the binary XML format.
#:
#: A chunk's type is a 16-bit value; the 32-bit constants below are the ones
#: the AOSP resource code spells them with, so they are kept as the low half
#: of those constants.
RES_STRING_POOL_TYPE = 0x0001
RES_XML_RESOURCE_MAP_TYPE = 0x0180
RES_XML_START_NAMESPACE_TYPE = 0x0100
RES_XML_END_NAMESPACE_TYPE = 0x0101
RES_XML_START_ELEMENT_TYPE = 0x0102
RES_XML_END_ELEMENT_TYPE = 0x0103
RES_XML_CDATA_TYPE = 0x0104

#: The value types an attribute's typed value can hold.
TYPE_NULL = 0x00
TYPE_REFERENCE = 0x01
TYPE_STRING = 0x03
TYPE_INT_DEC = 0x10
TYPE_INT_HEX = 0x11
TYPE_INT_BOOLEAN = 0x12

#: The namespace URI Android's own attributes live in.
ANDROID_NAMESPACE = "http://schemas.android.com/apk/res/android"

#: The sentinel a chunk's "no comment" field holds.
NO_ENTRY = 0xFFFFFFFF


class AxmlFormatError(ValueError):
    """The bytes are not a binary XML document this reader understands."""


@dataclass(frozen=True)
class AxmlAttribute:
    """One attribute of one element."""

    namespace: str | None
    """The namespace URI, or ``None`` for an attribute with no namespace."""

    name: str
    """The attribute's local name."""

    value: str | int | bool | None
    """The value.

    A string attribute gives the text; an integer attribute gives the number;
    a boolean attribute gives ``True`` or ``False``. A reference or an
    unrecognised value gives ``None`` — the reader does not follow resource
    references, because a benchmark that quotes one would be quoting an
    identifier it has not resolved.
    """

    raw: str | None = None
    """The value as it appears in the string pool, before any typing."""


@dataclass(frozen=True)
class AxmlElement:
    """One element of the document."""

    name: str
    """The element's local name, e.g. ``uses-sdk``."""

    namespace: str | None = None
    """The namespace URI, or ``None``."""

    attributes: tuple[AxmlAttribute, ...] = ()
    """The element's attributes, in the order the document lists them."""

    children: tuple[AxmlElement, ...] = ()
    """The elements nested inside this one, in document order."""

    def attribute(
        self, name: str, namespace: str | None = ANDROID_NAMESPACE
    ) -> AxmlAttribute | None:
        """The attribute with this name, or ``None``.

        The default namespace is Android's, which is where every attribute of
        a manifest that matters here lives: ``minSdkVersion`` is an Android
        attribute, and an unqualified ``name`` on a component is not.
        """
        for attribute in self.attributes:
            if attribute.name == name and attribute.namespace == namespace:
                return attribute
        return None

    def value(
        self, name: str, namespace: str | None = ANDROID_NAMESPACE
    ) -> str | int | bool | None:
        """The value of the attribute with this name, or ``None``."""
        attribute = self.attribute(name, namespace)
        return attribute.value if attribute is not None else None

    def find_all(self, name: str) -> list[AxmlElement]:
        """Every element with this local name, at any depth."""
        found: list[AxmlElement] = []
        if self.name == name:
            found.append(self)
        for child in self.children:
            found.extend(child.find_all(name))
        return found

    def find(self, name: str) -> AxmlElement | None:
        """The first element with this local name, or ``None``."""
        found = self.find_all(name)
        return found[0] if found else None


class _StringPool:
    """The strings a binary XML document draws its names and values from."""

    def __init__(self, data: bytes, offset: int) -> None:
        chunk_type, header_size, _chunk_size = struct.unpack_from("<HHI", data, offset)
        if chunk_type != RES_STRING_POOL_TYPE:
            raise AxmlFormatError(f"expected a string pool, found 0x{chunk_type:08x}")
        string_count, style_count, flags, strings_start, styles_start = struct.unpack_from(
            "<IIIII", data, offset + 8
        )
        del style_count, styles_start
        self.is_utf8 = bool(flags & 0x100)
        offsets = struct.unpack_from(f"<{string_count}I", data, offset + header_size)
        self.strings: list[str] = []
        base = offset + strings_start
        for entry in offsets:
            self.strings.append(self._read_string(data, base + entry))

    def _read_string(self, data: bytes, offset: int) -> str:
        if self.is_utf8:
            # UTF-8: a ULEB128 character count, a ULEB128 byte count, the
            # bytes, and a terminating NUL.
            _characters, offset = _uleb128(data, offset)
            byte_count, offset = _uleb128(data, offset)
            return data[offset : offset + byte_count].decode("utf-8", errors="replace")
        # UTF-16: a 16-bit length, the characters, and a terminating NUL.
        (length,) = struct.unpack_from("<H", data, offset)
        offset += 2
        if length & 0x8000:
            # The high bit means the real length is a 32-bit value.
            (length,) = struct.unpack_from("<I", data, offset)
            offset += 4
        return data[offset : offset + length * 2].decode("utf-16-le", errors="replace")

    def get(self, index: int) -> str:
        """The string at this index, or an empty string for the sentinel."""
        if index == NO_ENTRY or index >= len(self.strings):
            return ""
        return self.strings[index]


def _uleb128(data: bytes, offset: int) -> tuple[int, int]:
    """Read an unsigned LEB128 value, returning ``(value, next_offset)``."""
    result = 0
    shift = 0
    while True:
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, offset
        shift += 7


class BinaryXml:
    """A decoded binary XML document."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pool = _StringPool(data, 8)
        self.root = self._read_document()

    def _read_document(self) -> AxmlElement:
        """Walk the chunks, building the element tree.

        The document is a flat list of chunks — start element, end element,
        namespace — so the tree is built with a stack: a start element pushes,
        an end element pops.
        """
        data = self._data
        offset = 8
        stack: list[list[AxmlElement]] = [[]]
        while offset < len(data):
            chunk_type, header_size, chunk_size = struct.unpack_from("<HHI", data, offset)
            if chunk_size == 0:
                break
            if chunk_type == RES_XML_START_ELEMENT_TYPE:
                element = self._read_element(offset, header_size)
                stack[-1].append(element)
                stack.append(list(element.children))
            elif chunk_type == RES_XML_END_ELEMENT_TYPE:
                if len(stack) > 1:
                    finished = stack.pop()
                    parent = stack[-1]
                    if parent:
                        # Rebuild the parent with the finished children: the
                        # element was pushed before its children were known.
                        rebuilt = AxmlElement(
                            name=parent[-1].name,
                            namespace=parent[-1].namespace,
                            attributes=parent[-1].attributes,
                            children=tuple(finished),
                        )
                        parent[-1] = rebuilt
            offset += chunk_size
        roots = stack[0]
        return roots[0] if roots else AxmlElement(name="")

    def _read_element(self, offset: int, header_size: int) -> AxmlElement:
        data = self._data
        (
            namespace_idx,
            name_idx,
            attribute_start,
            attribute_size,
            attribute_count,
        ) = struct.unpack_from("<IIHHH", data, offset + header_size)
        attributes: list[AxmlAttribute] = []
        # The attribute block starts after the node header and the attribute
        # extension, and ``attribute_start`` says how far into the extension
        # it begins.
        base = offset + header_size + attribute_start
        for index in range(attribute_count):
            entry = base + index * attribute_size
            (
                attr_ns,
                attr_name,
                attr_raw,
                typed_size,
                reserved,
                data_type,
                data_value,
            ) = struct.unpack_from("<IIIH B B I".replace(" ", ""), data, entry)
            del typed_size, reserved
            raw = self._pool.get(attr_raw) if attr_raw != NO_ENTRY else None
            attributes.append(
                AxmlAttribute(
                    namespace=self._pool.get(attr_ns) or None,
                    name=self._pool.get(attr_name),
                    value=self._typed_value(data_type, data_value, raw),
                    raw=raw,
                )
            )
        return AxmlElement(
            name=self._pool.get(name_idx),
            namespace=self._pool.get(namespace_idx) or None,
            attributes=tuple(attributes),
        )

    def _typed_value(
        self, data_type: int, data_value: int, raw: str | None
    ) -> str | int | bool | None:
        """The value of a typed value, in the type it was stored as.

        A string keeps its text. An integer keeps its number. A boolean keeps
        its truth. Anything else — a reference, a null — is ``None``, because
        the reader does not resolve references and a benchmark must not quote
        an identifier it has not looked up.
        """
        if data_type == TYPE_STRING:
            return self._pool.get(data_value)
        if data_type in (TYPE_INT_DEC, TYPE_INT_HEX):
            return data_value
        if data_type == TYPE_INT_BOOLEAN:
            return data_value != 0
        if data_type == TYPE_NULL:
            return None
        del raw
        return None


def read_manifest(apk_path: Path) -> BinaryXml:
    """The ``AndroidManifest.xml`` inside an APK, decoded."""
    with zipfile.ZipFile(apk_path) as archive:
        data = archive.read("AndroidManifest.xml")
    return BinaryXml(data)
