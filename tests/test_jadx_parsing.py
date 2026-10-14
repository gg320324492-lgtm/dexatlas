"""JADX source parsing.

These exercise the pure parsing helpers against Java-shaped text. They need no JADX
installation; the subprocess path is covered separately by the slow suite.
"""

from __future__ import annotations

from pathlib import Path

from dexatlas.core.models import ClassKind
from dexatlas.tools.jadx.adapter import JadxBackend

SAMPLE_JAVA = """package com.example.demo;

import android.os.Bundle;

public class MainActivity extends android.app.Activity {
    private static final String TAG = "MainActivity";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (savedInstanceState != null) {
            restore(savedInstanceState);
        }
    }

    private void restore(Bundle state) {
        String key = "state";
        Log.d(TAG, "restoring " + key + " }");
    }

    static class Helper {
        void help() {
        }
    }
}
"""

EMPTY_METHOD_JAVA = """package com.example.demo;

public class Empty {
    void nothing() {
    }
}
"""


def _write(tmp_path: Path, text: str, name: str = "MainActivity.java") -> Path:
    sources = tmp_path / "jadx" / "sources" / "com" / "example" / "demo"
    sources.mkdir(parents=True, exist_ok=True)
    path = sources / name
    path.write_text(text, encoding="utf-8")
    return tmp_path / "jadx"


def test_class_name_is_derived_from_package_and_path(jadx: JadxBackend, tmp_path: Path) -> None:
    output = _write(tmp_path, SAMPLE_JAVA)

    assert (
        jadx._class_name(
            output / "sources" / "com" / "example" / "demo" / "MainActivity.java",
            output / "sources",
            SAMPLE_JAVA,
        )
        == "com.example.demo.MainActivity"
    )


def test_class_kind_is_detected(jadx: JadxBackend) -> None:
    assert jadx._class_kind(SAMPLE_JAVA) == ClassKind.CLASS
    assert jadx._class_kind("public interface Foo {}") == ClassKind.INTERFACE
    assert jadx._class_kind("enum Color { RED }") == ClassKind.ENUM


def test_finds_top_level_methods(jadx: JadxBackend) -> None:
    names = [span.name for span in jadx._method_spans(SAMPLE_JAVA)]

    assert "onCreate" in names
    assert "restore" in names


def test_control_flow_is_not_a_method_declaration(jadx: JadxBackend) -> None:
    """``for (...) {`` inside a body must never register as a method."""
    names = [span.name for span in jadx._method_spans(SAMPLE_JAVA)]

    assert "if" not in names
    assert "d" not in names


def test_extracts_a_method_body(jadx: JadxBackend, tmp_path: Path) -> None:
    output = _write(tmp_path, SAMPLE_JAVA)

    body = jadx.read_method_source("com.example.demo.MainActivity", "restore", output)

    assert body is not None
    assert body.strip().startswith("private void restore(Bundle state) {")
    assert body.strip().endswith("}")
    assert "Log.d(TAG" in body


def test_extracted_body_does_not_leak_into_the_next_method(
    jadx: JadxBackend, tmp_path: Path
) -> None:
    """Brace matching must stop at the right ``}`` even with nested blocks and a
    brace character inside a string literal."""
    output = _write(tmp_path, SAMPLE_JAVA)

    body = jadx.read_method_source("com.example.demo.MainActivity", "onCreate", output)

    assert body is not None
    assert body.count("{") == body.count("}")
    assert "restore(savedInstanceState)" in body
    assert "Log.d" not in body


def test_brace_inside_string_literal_does_not_truncate_the_body(
    jadx: JadxBackend, tmp_path: Path
) -> None:
    """``restore`` contains ``" }"`` in a string literal. Treating that brace as code
    would end the method mid-body and silently return a truncated snippet."""
    output = _write(tmp_path, SAMPLE_JAVA)

    body = jadx.read_method_source("com.example.demo.MainActivity", "restore", output)

    assert body is not None
    # The literal is intact, so the scan passed over it rather than counting it.
    assert '"restoring " + key + " }"' in body
    # And the real closing brace follows the statement, not the literal.
    assert body.rstrip().endswith('" }");\n    }')


def test_unknown_method_returns_none(jadx: JadxBackend, tmp_path: Path) -> None:
    output = _write(tmp_path, SAMPLE_JAVA)

    assert jadx.read_method_source("com.example.demo.MainActivity", "nope", output) is None


def test_unknown_class_returns_none(jadx: JadxBackend, tmp_path: Path) -> None:
    output = _write(tmp_path, SAMPLE_JAVA)

    assert jadx.read_class_source("com.example.demo.Missing", output) is None


def test_nested_class_resolves_to_its_outer_file(jadx: JadxBackend, tmp_path: Path) -> None:
    output = _write(tmp_path, SAMPLE_JAVA)

    source = jadx.read_class_source("com.example.demo.MainActivity$Helper", output)

    assert source is not None
    assert "class Helper" in source


def test_method_with_empty_body(jadx: JadxBackend, tmp_path: Path) -> None:
    output = _write(tmp_path, EMPTY_METHOD_JAVA, "Empty.java")

    body = jadx.read_method_source("com.example.demo.Empty", "nothing", output)

    assert body is not None
    assert body.strip().endswith("}")


def test_jadx_placeholders_are_recognised_as_not_decompiled() -> None:
    assert JadxBackend.method_decompiled('void f() { Log.d("a"); }') is True
    assert (
        JadxBackend.method_decompiled(
            'throw new UnsupportedOperationException("Method not decompiled");'
        )
        is False
    )
    assert JadxBackend.method_decompiled("// JADX ERROR: Method code generation failed") is False
    assert JadxBackend.method_decompiled("/* Method could not be decompiled */") is False
