"""What the ``decompiled`` flag on an indexed method actually says.

The flag is named after decompilation, so it has to answer the decompilation
question: did the decompiler produce Java for this method? It used to answer a
different one — Androguard's "does this method have a code item" — which is
true of nearly every method in an APK and says nothing at all about whether
the code can be read.

These tests exercise the mapping from what JADX wrote to what the index says.
They need no JADX installation: the backend's output is written to disk and
read back, exactly as it is after a real run.
"""

from __future__ import annotations

from pathlib import Path

from dexatlas.core.models import MethodRef
from dexatlas.core.pipeline import _apply_decompilation
from dexatlas.tools.jadx.adapter import JadxBackend

#: A class JADX decompiled, with one method it could not.
MIXED_JAVA = """package com.example.demo;

public class Crypto {
    public static String sign(String a, String b) {
        return a + b;
    }

    /* Method could not be decompiled */
    public static String broken(String a) {
        throw new UnsupportedOperationException("Method not decompiled");
    }
}
"""

#: A class with a constructor and a static initializer — the two methods whose
#: Java names differ from their DEX names.
CONSTRUCTOR_JAVA = """package com.example.demo;

public class Crypto {
    static {
        System.out.println("init");
    }

    public Crypto() {
    }
}
"""

#: A class with a nested class, which shares the outer class's file.
NESTED_JAVA = """package com.example.demo;

public class Outer {
    public void run() {
    }

    public static class Helper {
        public void help() {
        }
    }
}
"""

#: A class JADX decompiled with a caveat. The warning belongs to the class,
#: and the body behind it is real code.
WARNED_JAVA = """package com.example.demo;

public class NetworkClient {
    /* JADX WARN: Type inference failed for: r0v2, types: [java.lang.String] */
    public static String post(String str, String str2) {
        return str;
    }
}
"""

#: An obfuscated class with a method named exactly what the class is called.
#: JADX elided the trivial constructor, so the only thing called "a" is the
#: method — and it is not a constructor.
SAME_NAME_JAVA = """package a.a;

public class a {
    public String a(String str) {
        return str;
    }
}
"""


def _write(tmp_path: Path, text: str, name: str = "Crypto.java") -> Path:
    """Write a Java file where JADX would have written one."""
    sources = tmp_path / "jadx" / "sources" / "com" / "example" / "demo"
    sources.mkdir(parents=True, exist_ok=True)
    (sources / name).write_text(text, encoding="utf-8")
    return tmp_path / "jadx"


def _method(name: str, class_name: str = "com.example.demo.Crypto") -> MethodRef:
    return MethodRef(class_name=class_name, name=name, descriptor="()V")


# -- what JADX produced ------------------------------------------------------


def test_a_method_jadx_decompiled_is_marked_decompiled(jadx: JadxBackend, tmp_path: Path) -> None:
    output = _write(tmp_path, MIXED_JAVA)

    status = jadx.decompilation_status(output)
    entry = status["com.example.demo.Crypto"]

    assert entry.method_status("com.example.demo.Crypto", "sign") is True


def test_a_jadx_placeholder_is_not_a_decompilation(jadx: JadxBackend, tmp_path: Path) -> None:
    """JADX writes a stub for a method it could not reconstruct.

    The stub looks like a method in every other respect, so nothing but the
    marker tells the two apart.
    """
    output = _write(tmp_path, MIXED_JAVA)

    status = jadx.decompilation_status(output)
    entry = status["com.example.demo.Crypto"]

    assert entry.method_status("com.example.demo.Crypto", "broken") is False


def test_a_method_jadx_never_wrote_has_no_status(jadx: JadxBackend, tmp_path: Path) -> None:
    """Absent is not the same as failed: JADX wrote no Java for this method at all.

    An abstract method, a native method and a method JADX elided all land
    here, and none of them is a decompilation failure.
    """
    output = _write(tmp_path, MIXED_JAVA)

    status = jadx.decompilation_status(output)
    entry = status["com.example.demo.Crypto"]

    assert entry.method_status("com.example.demo.Crypto", "absent") is None


def test_a_jadx_warning_is_not_a_failed_decompilation(jadx: JadxBackend, tmp_path: Path) -> None:
    """JADX writes a warning above a method it decompiled anyway.

    The body behind the warning is real code. Reading the warning as a failure
    marked working methods as unreadable — which is what it did to the demo
    application's ``NetworkClient.post``.
    """
    output = _write(tmp_path, WARNED_JAVA, "NetworkClient.java")

    status = jadx.decompilation_status(output)
    entry = status["com.example.demo.NetworkClient"]

    assert entry.method_status("com.example.demo.NetworkClient", "post") is True


def test_the_constructor_is_matched_by_the_class_name(jadx: JadxBackend, tmp_path: Path) -> None:
    """A constructor is ``<init>`` in the DEX and the class's own name in Java."""
    output = _write(tmp_path, CONSTRUCTOR_JAVA)

    status = jadx.decompilation_status(output)
    entry = status["com.example.demo.Crypto"]

    assert entry.method_status("com.example.demo.Crypto", "<init>") is True


def test_a_method_named_after_its_class_is_not_its_constructor(
    jadx: JadxBackend, tmp_path: Path
) -> None:
    """An obfuscated class can have a method called exactly what the class is called.

    A constructor is written under the class's own name, so the name alone
    cannot tell the two apart. The return type can: a constructor has none.
    """
    output = _write(tmp_path, SAME_NAME_JAVA, "a.java")

    status = jadx.decompilation_status(output)
    entry = status["a.a.a"]

    assert entry.method_status("a.a.a", "a") is True
    # JADX elided the trivial constructor, so there is no decompiled source
    # for it — and the method of the same name must not stand in for it.
    assert entry.method_status("a.a.a", "<init>") is None


def test_the_static_initializer_is_matched_too(jadx: JadxBackend, tmp_path: Path) -> None:
    """``<clinit>`` is a ``static { ... }`` block, which is not a method signature."""
    output = _write(tmp_path, CONSTRUCTOR_JAVA)

    status = jadx.decompilation_status(output)
    entry = status["com.example.demo.Crypto"]

    assert entry.method_status("com.example.demo.Crypto", "<clinit>") is True


def test_a_nested_class_is_read_from_its_outer_file(jadx: JadxBackend, tmp_path: Path) -> None:
    """JADX writes one file per top-level class; a nested class lives inside it."""
    output = _write(tmp_path, NESTED_JAVA, "Outer.java")

    status = jadx.decompilation_status(output)

    assert "com.example.demo.Outer" in status
    entry = status["com.example.demo.Outer"]
    assert entry.method_status("com.example.demo.Outer$Helper", "help") is True


def test_a_class_jadx_never_wrote_is_absent_from_the_status(
    jadx: JadxBackend, tmp_path: Path
) -> None:
    output = _write(tmp_path, MIXED_JAVA)

    status = jadx.decompilation_status(output)

    assert "com.example.demo.Other" not in status


# -- what the index says -----------------------------------------------------


def test_only_the_methods_jadx_decompiled_are_marked(jadx: JadxBackend, tmp_path: Path) -> None:
    """The flag is set from JADX's own output, and from nothing else.

    Androguard knows whether a method has bytecode; that is a different
    question, and answering it here would put a claim in the index that no
    decompiler ever made.
    """
    output = _write(tmp_path, MIXED_JAVA)
    status = jadx.decompilation_status(output)

    methods = [
        _method("sign"),
        _method("broken"),
        _method("absent"),
    ]
    _apply_decompilation(methods, status)

    assert [m.decompiled for m in methods] == [True, False, False]


def test_a_method_of_a_class_jadx_never_wrote_is_not_marked(
    jadx: JadxBackend, tmp_path: Path
) -> None:
    output = _write(tmp_path, MIXED_JAVA)
    status = jadx.decompilation_status(output)

    methods = [_method("sign", class_name="com.example.demo.Other")]
    _apply_decompilation(methods, status)

    assert methods[0].decompiled is False


def test_a_method_of_a_nested_class_is_marked_from_the_outer_file(
    jadx: JadxBackend, tmp_path: Path
) -> None:
    output = _write(tmp_path, NESTED_JAVA, "Outer.java")
    status = jadx.decompilation_status(output)

    methods = [_method("help", class_name="com.example.demo.Outer$Helper")]
    _apply_decompilation(methods, status)

    assert methods[0].decompiled is True
