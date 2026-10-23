"""Resolving a locator against the analysis that claims to have produced it.

A locator is a pointer, and a pointer that looks right is not a pointer that
arrives. These tests are about the difference: a workspace that holds the thing
the locator names, and a workspace that does not.

The workspace here is written by the test rather than by a backend, so that the
question asked is the one about the resolver and not about JADX or Apktool. The
backends' own layouts are exercised where the analysis is really run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.core.locators import (
    InvalidLocatorError,
    LocatorKind,
    LocatorResolver,
    ResolutionReason,
    parse_locator,
)

#: One class, declared twice over: once as Java, once as smali. Both spell two
#: overloads of ``sign``, so a locator that names one of them has to say which.
JAVA_SOURCE = """package com.example.demo;

public final class Crypto {
    public static String sign(String key) {
        return key;
    }

    public static String sign(String key, String salt) {
        return key + salt;
    }
}
"""

SMALI_SOURCE = """.class public final Lcom/example/demo/Crypto;
.super Ljava/lang/Object;

.method public static sign(Ljava/lang/String;)Ljava/lang/String;
    .locals 0
    return-object p0
.end method

.method public static sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;
    .locals 0
    return-object p0
.end method
"""

MANIFEST_SOURCE = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:label="demo">
        <activity android:name="com.example.demo.MainActivity" android:exported="true" />
    </application>
</manifest>
"""

ONE_ARGUMENT = "(Ljava/lang/String;)Ljava/lang/String;"
TWO_ARGUMENTS = "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A workspace holding one class, in the trees a backend writes."""
    java = tmp_path / "jadx" / "sources" / "com" / "example" / "demo"
    java.mkdir(parents=True)
    (java / "Crypto.java").write_text(JAVA_SOURCE, encoding="utf-8")

    smali = tmp_path / "apktool" / "smali" / "com" / "example" / "demo"
    smali.mkdir(parents=True)
    (smali / "Crypto.smali").write_text(SMALI_SOURCE, encoding="utf-8")

    (tmp_path / "apktool" / "AndroidManifest.xml").write_text(MANIFEST_SOURCE, encoding="utf-8")
    return tmp_path


@pytest.fixture
def resolver(workspace: Path) -> LocatorResolver:
    return LocatorResolver(workspace, dex_files=["classes.dex"])


# -- what a locator is ------------------------------------------------------


@pytest.mark.parametrize(
    ("locator", "kind"),
    [
        ("jadx:sources/com/example/demo/Crypto.java", LocatorKind.SOURCE_PATH),
        ("jadx:sources/com/example/demo/Crypto.java#sign", LocatorKind.SOURCE_MEMBER),
        ("apktool:AndroidManifest.xml", LocatorKind.SOURCE_PATH),
        ("apktool:smali/com/example/demo/Crypto.smali#sign", LocatorKind.SOURCE_MEMBER),
        ("androguard:classes.dex", LocatorKind.DEX_FILE),
        ("androguard:classes.dex#com.example.demo.Crypto", LocatorKind.DEX_CLASS),
        ("androguard:classes.dex#com.example.demo.Crypto#TAG", LocatorKind.DEX_MEMBER),
        ("androguard:classes.dex#com.example.demo.Crypto.sign()V", LocatorKind.DEX_MEMBER),
        (
            "androguard:classes.dex#com.example.demo.Crypto.sign()V->com.example.demo.Other.hash()V",
            LocatorKind.DEX_CALL_EDGE,
        ),
        ("androguard:classes.dex#str/api_key", LocatorKind.DEX_STRING),
        ("jadx:error/not_installed", LocatorKind.TOOL_ERROR),
    ],
)
def test_every_shape_of_locator_is_read_as_what_it_is(locator: str, kind: LocatorKind) -> None:
    assert parse_locator(locator).kind is kind


def test_the_tool_and_the_place_are_told_apart() -> None:
    parsed = parse_locator("jadx:sources/com/example/demo/Crypto.java#sign")

    assert parsed.tool == "jadx"
    assert parsed.place == "sources/com/example/demo/Crypto.java"
    assert parsed.fragment == "sign"


@pytest.mark.parametrize(
    "locator",
    [
        "sources/com/example/demo/Crypto.java",
        "jadx:",
        "jadx:sources/com/example/demo/Crypto.java#",
        "unknown:sources/com/example/demo/Crypto.java",
        "jadx:/etc/passwd",
        "jadx:../../../etc/passwd",
        "jadx:C:/Windows/System32/drivers/etc/hosts",
        "jadx:sources\\com\\example\\demo\\Crypto.java",
    ],
)
def test_a_locator_that_is_not_one_is_refused(locator: str) -> None:
    """An unfamiliar locator is not one to guess at."""
    with pytest.raises(InvalidLocatorError):
        parse_locator(locator)


# -- the trees the backends wrote -------------------------------------------


def test_a_file_the_analysis_holds_resolves(resolver: LocatorResolver) -> None:
    resolution = resolver.resolve("jadx:sources/com/example/demo/Crypto.java")

    assert resolution.ok
    assert resolution.reason is ResolutionReason.RESOLVED
    assert resolution.path is not None
    assert resolution.path.name == "Crypto.java"


def test_a_directory_resolves_too(resolver: LocatorResolver) -> None:
    """The decompilation record points at a whole tree of files, not at one."""
    assert resolver.resolve("jadx:sources").ok


def test_a_file_the_analysis_does_not_hold_does_not_resolve(resolver: LocatorResolver) -> None:
    resolution = resolver.resolve("jadx:sources/com/example/demo/Missing.java")

    assert not resolution.ok
    assert resolution.reason is ResolutionReason.MISSING_PLACE


def test_a_locator_into_a_tree_that_was_never_written_is_absent_not_missing(
    tmp_path: Path,
) -> None:
    """A backend that did not run wrote nothing, so it named nothing here."""
    resolver = LocatorResolver(tmp_path, dex_files=["classes.dex"])

    resolution = resolver.resolve("jadx:sources/com/example/demo/Crypto.java")

    assert not resolution.ok
    assert resolution.reason is ResolutionReason.BACKEND_ABSENT


def test_a_locator_cannot_climb_out_of_the_tree_it_belongs_to(workspace: Path) -> None:
    """A path that leaves the analysis names something outside it."""
    resolver = LocatorResolver(workspace, dex_files=["classes.dex"])

    resolution = resolver.resolve("jadx:../../etc/passwd")

    assert not resolution.ok
    assert resolution.reason is ResolutionReason.MALFORMED


def test_a_symlink_out_of_the_tree_does_not_resolve(workspace: Path, tmp_path: Path) -> None:
    """The path may look right and still leave the analysis."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "Elsewhere.java").write_text(JAVA_SOURCE, encoding="utf-8")
    link = workspace / "jadx" / "sources" / "com" / "example" / "demo" / "Linked.java"
    link.symlink_to(outside / "Elsewhere.java")

    resolver = LocatorResolver(workspace, dex_files=["classes.dex"])

    resolution = resolver.resolve("jadx:sources/com/example/demo/Linked.java")

    assert not resolution.ok
    assert resolution.reason is ResolutionReason.UNSAFE_PATH


# -- what a file declares ---------------------------------------------------


def test_a_method_the_source_declares_resolves(resolver: LocatorResolver) -> None:
    resolution = resolver.resolve("jadx:sources/com/example/demo/Crypto.java#sign")

    assert resolution.ok


def test_a_method_the_source_does_not_declare_does_not_resolve(
    resolver: LocatorResolver,
) -> None:
    """A method that is not in the file is not there, however well it is spelled."""
    resolution = resolver.resolve("jadx:sources/com/example/demo/Crypto.java#encrypt")

    assert not resolution.ok
    assert resolution.reason is ResolutionReason.MISSING_MEMBER


def test_the_descriptor_tells_the_overloads_apart(resolver: LocatorResolver) -> None:
    """Two methods share the name, and the descriptor says which one.

    A Java source does not spell the descriptor, so the narrowing is by the
    number of arguments -- which is what tells the two apart in the source the
    reader is sent to.
    """
    one = resolver.resolve(f"jadx:sources/com/example/demo/Crypto.java#sign{ONE_ARGUMENT}")
    two = resolver.resolve(f"jadx:sources/com/example/demo/Crypto.java#sign{TWO_ARGUMENTS}")
    none = resolver.resolve("jadx:sources/com/example/demo/Crypto.java#sign()Ljava/lang/String;")

    assert one.ok
    assert two.ok
    assert not none.ok
    assert none.reason is ResolutionReason.MISSING_MEMBER


def test_a_smali_descriptor_is_matched_exactly(resolver: LocatorResolver) -> None:
    """Smali spells the method the way the DEX does, so the match is exact."""
    right = resolver.resolve(f"apktool:smali/com/example/demo/Crypto.smali#sign{ONE_ARGUMENT}")
    wrong = resolver.resolve(
        "apktool:smali/com/example/demo/Crypto.smali#sign(I)Ljava/lang/String;"
    )

    assert right.ok
    assert not wrong.ok
    assert wrong.reason is ResolutionReason.MISSING_MEMBER


def test_a_call_of_the_method_is_not_a_declaration_of_it(resolver: LocatorResolver) -> None:
    """The file calls ``sign``; it does not declare it under that name.

    A call and a declaration share a shape, so the text in front of the name
    is what tells them apart. This file holds the name in its body only.
    """
    (
        resolver.workspace_root / "jadx" / "sources" / "com" / "example" / "demo" / "Caller.java"
    ).write_text(
        "package com.example.demo;\n\npublic final class Caller {\n"
        '    public String run() {\n        return Crypto.sign("k");\n    }\n}\n',
        encoding="utf-8",
    )

    assert resolver.resolve("jadx:sources/com/example/demo/Caller.java#run").ok
    assert not resolver.resolve("jadx:sources/com/example/demo/Caller.java#sign").ok


def test_a_smali_method_resolves(resolver: LocatorResolver) -> None:
    resolution = resolver.resolve("apktool:smali/com/example/demo/Crypto.smali#sign")

    assert resolution.ok


def test_a_smali_method_is_matched_by_its_descriptor(resolver: LocatorResolver) -> None:
    resolution = resolver.resolve(
        f"apktool:smali/com/example/demo/Crypto.smali#sign{TWO_ARGUMENTS}"
    )

    assert resolution.ok


def test_a_manifest_element_resolves(resolver: LocatorResolver) -> None:
    resolution = resolver.resolve("apktool:AndroidManifest.xml#/application")

    assert resolution.ok


def test_a_manifest_element_that_is_not_there_does_not_resolve(
    resolver: LocatorResolver,
) -> None:
    resolution = resolver.resolve("apktool:AndroidManifest.xml#/service")

    assert not resolution.ok
    assert resolution.reason is ResolutionReason.MISSING_MEMBER


# -- the dex files -----------------------------------------------------------


def test_a_class_the_analysis_holds_resolves(resolver: LocatorResolver) -> None:
    resolution = resolver.resolve("androguard:classes.dex#com.example.demo.Crypto")

    assert resolution.ok


def test_a_class_the_analysis_does_not_hold_does_not_resolve(
    resolver: LocatorResolver,
) -> None:
    """The analysis decoded the APK, so a class it never saw is not in it."""
    resolution = resolver.resolve("androguard:classes.dex#com.example.demo.NotAClass")

    assert not resolution.ok
    assert resolution.reason is ResolutionReason.MISSING_MEMBER


def test_a_dex_file_the_apk_does_not_have_does_not_resolve(
    resolver: LocatorResolver,
) -> None:
    resolution = resolver.resolve("androguard:classes9.dex#com.example.demo.Crypto")

    assert not resolution.ok
    assert resolution.reason is ResolutionReason.UNKNOWN_DEX


def test_a_method_of_a_class_the_analysis_holds_resolves(resolver: LocatorResolver) -> None:
    resolution = resolver.resolve(
        "androguard:classes.dex#com.example.demo.Crypto#com.example.demo.Crypto.sign"
        f"{TWO_ARGUMENTS}"
    )

    assert resolution.ok


def test_a_method_the_class_does_not_declare_does_not_resolve(
    resolver: LocatorResolver,
) -> None:
    resolution = resolver.resolve(
        "androguard:classes.dex#com.example.demo.Crypto#com.example.demo.Crypto.encrypt()V"
    )

    assert not resolution.ok
    assert resolution.reason is ResolutionReason.MISSING_MEMBER


def test_a_call_edge_between_two_members_of_the_analysis_resolves(
    resolver: LocatorResolver,
) -> None:
    resolution = resolver.resolve(
        "androguard:classes.dex#com.example.demo.Crypto.sign"
        f"{ONE_ARGUMENT}->com.example.demo.Crypto.sign{TWO_ARGUMENTS}"
    )

    assert resolution.ok


def test_a_call_edge_to_a_class_that_is_not_in_the_analysis_does_not_resolve(
    resolver: LocatorResolver,
) -> None:
    resolution = resolver.resolve(
        "androguard:classes.dex#com.example.demo.Crypto.sign"
        f"{ONE_ARGUMENT}->com.example.demo.NotAClass.sign()V"
    )

    assert not resolution.ok
    assert resolution.reason is ResolutionReason.MISSING_MEMBER


def test_a_class_cannot_be_refuted_by_an_analysis_that_never_decoded_it(
    tmp_path: Path,
) -> None:
    """No smali means no way to ask the question, and no way to refute it either."""
    resolver = LocatorResolver(tmp_path, dex_files=["classes.dex"])

    resolution = resolver.resolve("androguard:classes.dex#com.example.demo.Crypto")

    assert resolution.ok


# -- a failure is a fact ----------------------------------------------------


def test_a_backend_failure_resolves(resolver: LocatorResolver) -> None:
    """There is no file behind ``jadx:error/not_installed``, and there is nothing to resolve.

    The failure itself is what the record is about, so the locator names the
    failure rather than a place.
    """
    resolution = resolver.resolve("jadx:error/not_installed")

    assert resolution.ok
    assert resolution.reason is ResolutionReason.TOOL_ERROR


def test_a_locator_of_an_unknown_backend_does_not_resolve(resolver: LocatorResolver) -> None:
    resolution = resolver.resolve("someother:source/Foo.java")

    assert not resolution.ok
    assert resolution.reason is ResolutionReason.UNKNOWN_BACKEND


# -- the resolver is given the workspace --------------------------------------


def test_the_resolver_answers_for_the_workspace_it_was_given(tmp_path: Path) -> None:
    """The workspace is an argument, and the resolver looks nowhere else."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    assert (
        not LocatorResolver(elsewhere, dex_files=["classes.dex"])
        .resolve("jadx:sources/com/example/demo/Crypto.java")
        .ok
    )
