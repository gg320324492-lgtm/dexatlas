"""A minimal DEX reader: class names, method names and DEX descriptors.

Deliberately independent of the tool under measurement. It reads the bytes of a
``classes*.dex`` entry straight out of an APK zip, following the DEX file
format directly (format spec: https://source.android.com/docs/core/runtime/dex-format).
Nothing here imports ``dexatlas``: a benchmark whose expectations are checked
with the tool it measures cannot catch the tool being wrong.

Only what a benchmark needs is decoded:

* the class table, with the DEX file each class came from;
* each class's methods, with their full DEX descriptor
  ``(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;``.

The descriptor is what tells two overloads apart, so it is decoded rather than
guessed: the method's prototype (return type plus parameter types) is
reassembled from the proto and type tables.
"""

from __future__ import annotations

import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path

_HEADER = struct.Struct("<8sI20sIIIIIIIIIIIIIIIIIIII")
_CLASS_DEF = struct.Struct("<IIIIIIII")
_METHOD_ID = struct.Struct("<HHI")
_PROTO_ID = struct.Struct("<III")


class DexFormatError(ValueError):
    """The bytes are not a DEX file this reader understands."""


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
        if shift > 35:
            raise DexFormatError("ULEB128 value is too long")


def _read_mutf8(data: bytes, offset: int) -> str:
    """Read a DEX string: a ULEB128 UTF-16 length, then MUTF-8 bytes.

    The length is a count of UTF-16 code units, not of bytes, so the bytes are
    decoded to a list of code units and then paired up. MUTF-8 encodes the
    null character as ``0xC0 0x80``; Python's decoder rejects that, so it is
    patched back after decoding.
    """
    _length, offset = _uleb128(data, offset)
    end = data.index(b"\x00", offset)
    raw = data[offset:end]
    decoded = raw.decode("utf-8", errors="replace")
    return decoded.replace("�", "\x00")


@dataclass(frozen=True)
class DexMethod:
    """One method, as the DEX file records it."""

    class_name: str
    """The descriptor of the defining class, e.g. ``Lcom/example/demo/Crypto;``."""

    name: str
    """The method's simple name, e.g. ``sign``."""

    descriptor: str
    """The full DEX descriptor, e.g. ``(Ljava/lang/String;)V``."""

    dex_name: str
    """The DEX file the method was defined in, e.g. ``classes2.dex``."""

    @property
    def signature(self) -> str:
        """``class.name(descriptor)`` — the form a caller would paste."""
        return f"{self.class_name}->{self.name}{self.descriptor}"

    @property
    def short_name(self) -> str:
        """``name(descriptor)`` without the owning class."""
        return f"{self.name}{self.descriptor}"


@dataclass(frozen=True)
class DexClass:
    """One class, as the DEX file records it."""

    name: str
    """The descriptor of the class, e.g. ``Lcom/example/demo/Crypto;``."""

    dex_name: str
    """The DEX file the class was defined in."""

    source_file: str | None
    """The ``.source`` name, when the class records one."""

    methods: tuple[DexMethod, ...]
    """The methods the class defines, in the DEX file's own order."""


class DexFile:
    """One ``classes*.dex`` file, read out of an APK."""

    def __init__(self, data: bytes, dex_name: str) -> None:
        self.dex_name = dex_name
        self._data = data
        self._strings: list[str] = []
        self._types: list[str] = []
        self._protos: list[tuple[str, list[str]]] = []
        self._method_ids: list[tuple[str, str, str]] = []
        self._read_header()
        self._read_strings()
        self._read_types()
        self._read_protos()
        self._read_method_ids()
        self.classes = self._read_classes()

    def _read_header(self) -> None:
        data = self._data
        if len(data) < 112:
            raise DexFormatError("file is too short to be a DEX")
        magic = data[:8]
        if magic[:4] != b"dex\n":
            raise DexFormatError(f"bad DEX magic: {magic!r}")
        (
            _magic,
            _checksum,
            _signature,
            _file_size,
            _header_size,
            _endian,
            _link_size,
            _link_off,
            _map_off,
            self.string_ids_size,
            self.string_ids_off,
            self.type_ids_size,
            self.type_ids_off,
            self.proto_ids_size,
            self.proto_ids_off,
            _field_ids_size,
            _field_ids_off,
            self.method_ids_size,
            self.method_ids_off,
            self.class_defs_size,
            self.class_defs_off,
            _data_size,
            _data_off,
        ) = _HEADER.unpack_from(data, 0)

    def _read_strings(self) -> None:
        data = self._data
        self._strings = []
        for index in range(self.string_ids_size):
            (offset,) = struct.unpack_from("<I", data, self.string_ids_off + index * 4)
            self._strings.append(_read_mutf8(data, offset))

    def _read_types(self) -> None:
        data = self._data
        self._types = []
        for index in range(self.type_ids_size):
            (descriptor_idx,) = struct.unpack_from("<I", data, self.type_ids_off + index * 4)
            self._types.append(self._strings[descriptor_idx])

    def _read_protos(self) -> None:
        data = self._data
        self._protos = []
        for index in range(self.proto_ids_size):
            shorty_idx, return_type_idx, parameters_off = _PROTO_ID.unpack_from(
                data, self.proto_ids_off + index * 12
            )
            del shorty_idx
            return_type = self._types[return_type_idx]
            parameters: list[str] = []
            if parameters_off != 0:
                size = struct.unpack_from("<I", data, parameters_off)[0]
                for slot in range(size):
                    (type_idx,) = struct.unpack_from("<H", data, parameters_off + 4 + slot * 2)
                    parameters.append(self._types[type_idx])
            self._protos.append((return_type, parameters))

    def _read_method_ids(self) -> None:
        data = self._data
        self._method_ids = []
        for index in range(self.method_ids_size):
            class_idx, proto_idx, name_idx = _METHOD_ID.unpack_from(
                data, self.method_ids_off + index * 8
            )
            return_type, parameters = self._protos[proto_idx]
            descriptor = f"({''.join(parameters)}){return_type}"
            self._method_ids.append((self._types[class_idx], self._strings[name_idx], descriptor))

    def _read_classes(self) -> list[DexClass]:
        data = self._data
        classes: list[DexClass] = []
        for index in range(self.class_defs_size):
            (
                class_idx,
                _access_flags,
                _superclass_idx,
                _interfaces_off,
                source_file_idx,
                _annotations_off,
                class_data_off,
                _static_values_off,
            ) = _CLASS_DEF.unpack_from(data, self.class_defs_off + index * 32)
            class_name = self._types[class_idx]
            source_file = self._strings[source_file_idx] if source_file_idx != 0xFFFFFFFF else None
            methods = self._read_class_data(class_data_off)
            classes.append(
                DexClass(
                    name=class_name,
                    dex_name=self.dex_name,
                    source_file=source_file,
                    methods=methods,
                )
            )
        return classes

    def _read_class_data(self, offset: int) -> tuple[DexMethod, ...]:
        if offset == 0:
            return ()
        data = self._data
        cursor = offset
        static_fields, cursor = _uleb128(data, cursor)
        instance_fields, cursor = _uleb128(data, cursor)
        direct_methods, cursor = _uleb128(data, cursor)
        virtual_methods, cursor = _uleb128(data, cursor)
        # Field entries are skipped: their index deltas are relative to the
        # previous field, so they have to be walked to reach the method ids.
        for _ in range(static_fields + instance_fields):
            _, cursor = _uleb128(data, cursor)  # field_idx_diff
            _, cursor = _uleb128(data, cursor)  # access_flags

        methods: list[DexMethod] = []
        for count in (direct_methods, virtual_methods):
            method_idx = 0
            for _ in range(count):
                diff, cursor = _uleb128(data, cursor)
                _, cursor = _uleb128(data, cursor)  # access_flags
                _, cursor = _uleb128(data, cursor)  # code_off
                method_idx += diff
                class_name, name, descriptor = self._method_ids[method_idx]
                methods.append(
                    DexMethod(
                        class_name=class_name,
                        name=name,
                        descriptor=descriptor,
                        dex_name=self.dex_name,
                    )
                )
        return tuple(methods)


def read_apk_classes(apk_path: Path) -> list[DexClass]:
    """Every class in every ``classes*.dex`` of an APK, in zip order.

    The DEX file each class came from is carried on the result, because a class
    that appears in more than one DEX is a fact about the sample and not a
    detail to be flattened away.
    """
    classes: list[DexClass] = []
    with zipfile.ZipFile(apk_path) as archive:
        names = sorted(n for n in archive.namelist() if n.endswith(".dex"))
        for name in names:
            dex = DexFile(archive.read(name), name)
            classes.extend(dex.classes)
    return classes


def read_apk_methods(apk_path: Path) -> list[DexMethod]:
    """Every method in every ``classes*.dex`` of an APK."""
    methods: list[DexMethod] = []
    for cls in read_apk_classes(apk_path):
        methods.extend(cls.methods)
    return methods
