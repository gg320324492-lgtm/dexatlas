"""Overload-safe method resolution.

A method resolved by name alone can return the wrong overload, and the error
travels straight into an agent's answer: the body of the wrong method reads
exactly like the body of the right one. The DEX descriptor is what tells two
overloads apart, the symbol index already stores it, and this file holds down
the behaviour that uses it.

Every test here has teeth: on the old implementation — which took the first
declaration whose name matched — the ones that matter fail. The break
experiment is in the report that came with this change.

The Java in these fixtures is written the way a decompiler writes it: the
methods in alphabetical order, the parameters named ``str`` and ``str2``, the
imports at the top. That matters, because the first declaration whose name
matched is the one the old code returned, and it has to be the wrong one for
the test to prove anything.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dexatlas.api.app import app
from dexatlas.config.settings import Settings, get_settings
from dexatlas.core.methods import (
    AmbiguousMethodError,
    JavaContext,
    is_descriptor,
    match_parameter_rank,
    match_type_rank,
    parse_java_type,
)
from dexatlas.core.models import (
    ApkMetadata,
    ClassKind,
    ClassRef,
    MethodRef,
    Project,
    ProjectStatus,
    Provenance,
    SourceKind,
)
from dexatlas.core.pipeline import Analyzer
from dexatlas.core.storage import Store
from dexatlas.tools.androguard.adapter import androguard_available
from dexatlas.tools.apktool.adapter import ApktoolBackend
from dexatlas.tools.jadx.adapter import JadxBackend

FAKE_SHA256 = "c" * 64

CLASS_NAME = "com.example.demo.Crypto"
NESTED_CLASS_NAME = "com.example.demo.Crypto$Helper"

#: The DEX descriptors of the three overloads of ``sign``. These are what the
#: index stores and what a caller has to send to pick one of them.
SIGN_INT = "(I)Ljava/lang/String;"
SIGN_ONE = "(Ljava/lang/String;)Ljava/lang/String;"
SIGN_TWO = "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"
NO_ARGS = "()V"

#: Two classes whose names are the same and whose packages are not. The
#: decompiler writes one of them bare and the other in full, and only the
#: descriptor tells which is which.
LOCAL_ALIAS_TYPE = "Lcom/example/demo/Alias;"
REMOTE_ALIAS_TYPE = "Lcom/example/demo/other/Alias;"
LOCAL_ALIAS = f"({LOCAL_ALIAS_TYPE})Ljava/lang/String;"
REMOTE_ALIAS = f"({REMOTE_ALIAS_TYPE})Ljava/lang/String;"

#: A class with three overloads of ``sign``, a method of its own name, a
#: constructor of the same name as a method, a nested class, and two classes
#: that share a simple name — the shapes that a name alone cannot tell apart.
JAVA_SOURCE = """package com.example.demo;

import java.util.List;

/* loaded from: classes.dex */
public final class Crypto {

    public final class Helper {
        public String assist(String str) {
            return str;
        }

        public String sign(String str) {
            return "nested";
        }
    }

    public Crypto() {
        seed();
    }

    public static void Crypto() {
    }

    public static String digest(String str) {
        return str;
    }

    public static String helper(Helper helper) {
        return "helped";
    }

    public static String join(List list) {
        return "joined";
    }

    public static String pick(Alias alias) {
        return "local";
    }

    public static String pick(com.example.demo.other.Alias alias) {
        return "remote";
    }

    public static void seed() {
    }

    public static String sign(int i) {
        return String.valueOf(i);
    }

    public static String sign(String str) {
        return str;
    }

    public static String sign(String str, String str2) {
        return str + str2;
    }
}
"""

#: The same class in Smali. A Smali header carries the DEX descriptor, so the
#: fallback path can be exact where the decompiled Java has to be interpreted.
SMALI_SOURCE = """.class public final Lcom/example/demo/Crypto;
.super Ljava/lang/Object;
.source "Crypto.java"


# direct methods
.method public constructor <init>()V
    .locals 0

    invoke-static {}, Lcom/example/demo/Crypto;->seed()V

    return-void
.end method

.method public static Crypto()V
    .locals 0

    return-void
.end method

.method public static digest(Ljava/lang/String;)Ljava/lang/String;
    .locals 1

    return-object p0
.end method

.method public static helper(Lcom/example/demo/Crypto$Helper;)Ljava/lang/String;
    .locals 1

    const-string v0, "helped"

    return-object v0
.end method

.method public static join(Ljava/util/List;)Ljava/lang/String;
    .locals 1

    const-string v0, "joined"

    return-object v0
.end method

.method public static pick(Lcom/example/demo/Alias;)Ljava/lang/String;
    .locals 1

    const-string v0, "local"

    return-object v0
.end method

.method public static pick(Lcom/example/demo/other/Alias;)Ljava/lang/String;
    .locals 1

    const-string v0, "remote"

    return-object v0
.end method

.method private static seed()V
    .locals 0

    return-void
.end method

.method public static sign(I)Ljava/lang/String;
    .locals 1

    invoke-static {p0}, Ljava/lang/String;->valueOf(I)Ljava/lang/String;

    move-result-object v0

    return-object v0
.end method

.method public static sign(Ljava/lang/String;)Ljava/lang/String;
    .locals 1

    return-object p0
.end method

.method public static sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;
    .locals 1

    new-instance v0, Ljava/lang/StringBuilder;

    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v0, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    return-object v0
.end method
"""

#: A class whose decompiled signatures JADX could not work out. Two overloads
#: of one name, both with a parameter it had to call ``var1``.
OPAQUE_JAVA = """package com.example.demo;

public class Opaque {
    public static String sign(var1) {
        return var1;
    }

    public static String sign(var2) {
        return var2;
    }
}
"""

#: The same trouble in the class the other tests use: two overloads whose
#: signatures JADX could not spell out, and nothing to tell them apart.
OPAQUE_CRYPTO = """package com.example.demo;

public final class Crypto {
    public static String sign(var1) {
        return var1;
    }

    public static String sign(var2) {
        return var2;
    }
}
"""

#: The methods of the fixture class, with the descriptors the index holds.
INDEXED_METHODS: list[tuple[str, str]] = [
    ("<init>", NO_ARGS),
    ("Crypto", NO_ARGS),
    ("digest", SIGN_ONE),
    ("helper", "(Lcom/example/demo/Crypto$Helper;)Ljava/lang/String;"),
    ("join", "(Ljava/util/List;)Ljava/lang/String;"),
    ("pick", LOCAL_ALIAS),
    ("pick", REMOTE_ALIAS),
    ("seed", NO_ARGS),
    ("sign", SIGN_INT),
    ("sign", SIGN_ONE),
    ("sign", SIGN_TWO),
]


@pytest.fixture
def workspace_with_sources(tmp_path: Path) -> tuple[Path, str]:
    """A workspace holding both representations of one class, and its index."""
    workspace = tmp_path / "workspace"
    project_id = Project.new_id(FAKE_SHA256)
    project_dir = workspace / "projects" / project_id

    java = project_dir / "jadx" / "sources" / "com" / "example" / "demo" / "Crypto.java"
    java.parent.mkdir(parents=True)
    java.write_text(JAVA_SOURCE, encoding="utf-8")

    smali = project_dir / "apktool" / "smali" / "com" / "example" / "demo" / "Crypto.smali"
    smali.parent.mkdir(parents=True)
    smali.write_text(SMALI_SOURCE, encoding="utf-8")

    store = Store.open(workspace / "dexatlas.db")
    store.save_project(
        Project(
            id=project_id,
            apk=ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=Path("demo.apk")),
            status=ProjectStatus.COMPLETED,
            tool_versions={"jadx": "1.5.2", "apktool": "2.11.1"},
        ),
        project_dir,
        manifest=None,
    )

    provenance = [
        Provenance(
            tool="androguard",
            tool_version="4.1.4",
            apk_sha256=FAKE_SHA256,
            locator="androguard:classes.dex#com.example.demo.Crypto",
        )
    ]
    store.save_symbols(
        project_id,
        [
            ClassRef(
                name=CLASS_NAME,
                kind=ClassKind.CLASS,
                access_flags=["public"],
                method_count=len(INDEXED_METHODS),
                provenance=provenance,
            )
        ],
        [
            MethodRef(
                class_name=CLASS_NAME,
                name=name,
                descriptor=descriptor,
                access_flags=["public"],
                provenance=provenance,
            )
            for name, descriptor in INDEXED_METHODS
        ],
        [],
        [],
        [],
    )
    return workspace, project_id


@pytest.fixture
def opaque_workspace(tmp_path: Path) -> tuple[Path, str]:
    """A workspace whose one class has two overloads with unreadable types."""
    workspace = tmp_path / "workspace"
    project_id = Project.new_id(FAKE_SHA256)
    project_dir = workspace / "projects" / project_id
    java = project_dir / "jadx" / "sources" / "com" / "example" / "demo" / "Opaque.java"
    java.parent.mkdir(parents=True)
    java.write_text(OPAQUE_JAVA, encoding="utf-8")

    store = Store.open(workspace / "dexatlas.db")
    store.save_project(
        Project(
            id=project_id,
            apk=ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=Path("opaque.apk")),
            status=ProjectStatus.COMPLETED,
        ),
        project_dir,
        manifest=None,
    )
    return workspace, project_id


@pytest.fixture(autouse=True)
def apktool_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the disassembler answer, without running it."""
    monkeypatch.setattr(ApktoolBackend, "resolve", lambda self: Path("apktool-stub"))


@pytest.fixture(autouse=True)
def jadx_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the decompiler answer, without running it."""
    monkeypatch.setattr(JadxBackend, "resolve", lambda self: Path("jadx-stub"))


@pytest.fixture
def jadx_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """The configuration the Smali fallback exists for."""
    monkeypatch.setattr(JadxBackend, "resolve", lambda self: None)


def _analyzer(workspace: Path) -> Analyzer:
    return Analyzer(Settings(workspace=workspace))


# -- the overloaded method ----------------------------------------------------


def test_a_descriptor_picks_the_overload_it_names(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """The overloads are different methods, and the descriptor says which."""
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    document = analyzer.method_source_document(project_id, CLASS_NAME, "sign", SIGN_ONE)

    assert document is not None
    assert "String sign(String str)" in document.text
    assert "String sign(String str, String str2)" not in document.text


def test_the_other_overload_is_the_other_body(
    workspace_with_sources: tuple[Path, str],
) -> None:
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    document = analyzer.method_source_document(project_id, CLASS_NAME, "sign", SIGN_TWO)

    assert document is not None
    assert "String sign(String str, String str2)" in document.text
    assert "return str + str2;" in document.text


def test_the_overload_of_another_type_is_its_own_body(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """The overload a name alone would have found first is not the one asked for.

    The declarations are in the order a decompiler writes them, so the first
    ``sign`` in the file is the one that takes an ``int``. An implementation
    that matched on the name returned that one for every request.
    """
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    document = analyzer.method_source_document(project_id, CLASS_NAME, "sign", SIGN_INT)

    assert document is not None
    assert "String sign(int i)" in document.text
    assert "String.valueOf(i)" in document.text


def test_a_name_that_matches_several_overloads_is_ambiguous(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """The old implementation took the first one it found.

    Returning that body is the bug: it reads like the right method and is
    not. The error has to name the candidates, with the descriptors that tell
    them apart.
    """
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    with pytest.raises(AmbiguousMethodError) as caught:
        analyzer.method_source_document(project_id, CLASS_NAME, "sign")

    candidates = caught.value.candidates
    assert {candidate.descriptor for candidate in candidates} == {
        SIGN_INT,
        SIGN_ONE,
        SIGN_TWO,
    }
    assert {candidate.name for candidate in candidates} == {"sign"}
    assert caught.value.class_name == CLASS_NAME
    assert caught.value.method_name == "sign"


def test_the_ambiguity_says_how_to_ask_again(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """A caller that is told what the candidates are can pick one."""
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    with pytest.raises(AmbiguousMethodError) as caught:
        analyzer.method_source_document(project_id, CLASS_NAME, "sign")

    spellings = {candidate.signature for candidate in caught.value.candidates}
    assert spellings == {f"sign{SIGN_INT}", f"sign{SIGN_ONE}", f"sign{SIGN_TWO}"}
    assert "a descriptor is needed" in caught.value.describe()


def test_a_name_that_matches_one_method_still_works(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """The ordinary case is unchanged: one method by that name, one body."""
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    document = analyzer.method_source_document(project_id, CLASS_NAME, "digest")

    assert document is not None
    assert "String digest(String str)" in document.text


def test_the_text_only_interface_still_answers(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """``method_source`` keeps its contract: a string, or nothing."""
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    assert analyzer.method_source(project_id, CLASS_NAME, "digest") is not None
    assert analyzer.method_source(project_id, CLASS_NAME, "sign", SIGN_ONE) is not None


# -- two classes that share a simple name -------------------------------------


def test_two_classes_with_one_simple_name_are_not_mixed_up(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """``Alias`` and ``other.Alias`` are different classes.

    The decompiler writes one of them bare and the other in full, and a
    translation that only compares simple names calls them the same class.
    """
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    local = analyzer.method_source_document(project_id, CLASS_NAME, "pick", LOCAL_ALIAS)
    remote = analyzer.method_source_document(project_id, CLASS_NAME, "pick", REMOTE_ALIAS)

    assert local is not None
    assert "String pick(Alias alias)" in local.text
    assert '"remote"' not in local.text

    assert remote is not None
    assert "String pick(com.example.demo.other.Alias alias)" in remote.text
    assert '"local"' not in remote.text


# -- the constructor ----------------------------------------------------------


def test_a_constructor_is_not_the_method_of_the_same_name(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """A class can have a constructor and a method of the very same name.

    Both are written under the class's own name in Java, and both have the
    descriptor ``()V`` — so the descriptor alone cannot tell them apart, and
    the index's name has to.
    """
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    document = analyzer.method_source_document(project_id, CLASS_NAME, "<init>", NO_ARGS)

    assert document is not None
    # The constructor's body calls seed(); the same-named method's does not.
    assert "seed();" in document.text
    assert "public Crypto() {" in document.text


def test_the_constructor_asked_for_by_its_java_name_is_ambiguous(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """``Crypto`` names the constructor and the method that shares its name."""
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    with pytest.raises(AmbiguousMethodError) as caught:
        analyzer.method_source_document(project_id, CLASS_NAME, "Crypto")

    assert len(caught.value.candidates) == 2
    assert {candidate.name for candidate in caught.value.candidates} == {"<init>", "Crypto"}


def test_the_same_named_method_is_still_reachable(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """Naming the method as the DEX names it is not ambiguous."""
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    document = analyzer.method_source_document(project_id, CLASS_NAME, "Crypto", NO_ARGS)

    assert document is not None
    assert "public static void Crypto()" in document.text
    assert "seed();" not in document.text


# -- the nested class ---------------------------------------------------------


def test_a_nested_class_method_is_the_nested_class_method(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """A nested class shares the file of the class that holds it.

    Its methods are not the outer class's methods, and a reader that is shown
    the outer class's method has been shown the wrong one.
    """
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    document = analyzer.method_source_document(project_id, NESTED_CLASS_NAME, "assist", SIGN_ONE)

    assert document is not None
    assert "String assist(String str)" in document.text


def test_a_method_of_the_same_name_in_a_nested_class_is_not_the_outer_one(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """The nested class has a ``sign(String)`` of its own.

    The two have the same name *and* the same signature, so the descriptor
    cannot tell them apart — only the class the request names can. The
    decompiler writes the nested class first, so an implementation that read
    the whole file returned the nested class's body for the outer class's
    method.
    """
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    outer = analyzer.method_source_document(project_id, CLASS_NAME, "sign", SIGN_ONE)
    nested = analyzer.method_source_document(project_id, NESTED_CLASS_NAME, "sign", SIGN_ONE)

    assert outer is not None
    assert '"nested"' not in outer.text
    assert "return str;" in outer.text

    assert nested is not None
    assert '"nested"' in nested.text


def test_a_nested_class_parameter_is_matched_by_its_own_name(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """``Helper`` in the source is ``Crypto$Helper`` in the DEX.

    The decompiler writes the nested class by its bare name, and only the
    file's own classes say which class that is.
    """
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    document = analyzer.method_source_document(
        project_id,
        CLASS_NAME,
        "helper",
        "(Lcom/example/demo/Crypto$Helper;)Ljava/lang/String;",
    )

    assert document is not None
    assert "String helper(Helper helper)" in document.text


# -- the Smali fallback -------------------------------------------------------


def test_the_smali_fallback_resolves_by_descriptor(
    workspace_with_sources: tuple[Path, str], jadx_unavailable: None
) -> None:
    """Smali carries the descriptor, so the fallback is exact."""
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    document = analyzer.method_source_document(project_id, CLASS_NAME, "sign", SIGN_TWO)

    assert document is not None
    assert document.text.startswith(".method")
    assert f"sign{SIGN_TWO}" in document.text.splitlines()[0]


def test_the_smali_fallback_reports_an_ambiguous_name(
    workspace_with_sources: tuple[Path, str], jadx_unavailable: None
) -> None:
    """Two blocks with one name, and no descriptor to tell them apart."""
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    with pytest.raises(AmbiguousMethodError) as caught:
        analyzer.method_source_document(project_id, CLASS_NAME, "sign")

    assert {candidate.descriptor for candidate in caught.value.candidates} == {
        SIGN_INT,
        SIGN_ONE,
        SIGN_TWO,
    }


def test_the_smali_fallback_finds_the_constructor(
    workspace_with_sources: tuple[Path, str], jadx_unavailable: None
) -> None:
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    document = analyzer.method_source_document(project_id, CLASS_NAME, "<init>", NO_ARGS)

    assert document is not None
    assert "constructor <init>" in document.text.splitlines()[0]


def test_the_smali_fallback_keeps_the_two_aliases_apart(
    workspace_with_sources: tuple[Path, str], jadx_unavailable: None
) -> None:
    """The bytecode names both classes in full, so it never mixes them up."""
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    local = analyzer.method_source_document(project_id, CLASS_NAME, "pick", LOCAL_ALIAS)
    remote = analyzer.method_source_document(project_id, CLASS_NAME, "pick", REMOTE_ALIAS)

    assert local is not None
    assert '"local"' in local.text
    assert '"remote"' not in local.text

    assert remote is not None
    assert '"remote"' in remote.text
    assert '"local"' not in remote.text


# -- a decompiled signature that says nothing ---------------------------------


def test_an_opaque_signature_is_matched_on_its_arity(
    opaque_workspace: tuple[Path, str],
) -> None:
    """JADX writes ``var1`` when it cannot work out a parameter's type.

    The type is gone, but the number of parameters is not, so an overload of a
    different length is still told apart.
    """
    workspace, project_id = opaque_workspace
    analyzer = _analyzer(workspace)

    document = analyzer.method_source_document(
        project_id, "com.example.demo.Opaque", "sign", SIGN_TWO
    )

    assert document is None, "the source has no two-parameter overload"


def test_an_opaque_signature_that_does_not_decide_is_ambiguous(
    opaque_workspace: tuple[Path, str],
) -> None:
    """Two overloads, one parameter each, and no type to go on.

    The arity is the same, so nothing distinguishes them and the request is
    ambiguous — the error says so rather than picking one.
    """
    workspace, project_id = opaque_workspace
    analyzer = _analyzer(workspace)

    with pytest.raises(AmbiguousMethodError) as caught:
        analyzer.method_source_document(project_id, "com.example.demo.Opaque", "sign", SIGN_ONE)

    assert len(caught.value.candidates) == 2


def test_the_bytecode_decides_when_the_decompiled_signature_cannot(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """A decompiler that could not work out a type writes the name twice.

    The bytecode carries the descriptor, so the fallback answers before the
    ambiguity is reported: a representation that can decide is used, and only
    a request that no representation can decide is an ambiguity.
    """
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    # The Java source is replaced by one whose signatures say nothing, while
    # the Smali beside it still names the overload exactly.
    java = (
        workspace
        / "projects"
        / project_id
        / "jadx"
        / "sources"
        / "com"
        / "example"
        / "demo"
        / "Crypto.java"
    )
    java.write_text(OPAQUE_CRYPTO, encoding="utf-8")

    document = analyzer.method_source_document(project_id, CLASS_NAME, "sign", SIGN_ONE)

    assert document is not None
    assert document.kind is SourceKind.SMALI
    assert f"sign{SIGN_ONE}" in document.text.splitlines()[0]


# -- the translation between the two spellings --------------------------------


def _context() -> JavaContext:
    """The context of the fixture class: its package and its own classes."""
    return JavaContext(
        package="com.example.demo",
        imports={"List": "java.util.List"},
        own_classes={"Crypto": "com/example/demo/Crypto"},
    )


def test_a_java_type_matches_the_descriptor_that_names_it() -> None:
    """``String`` in the source is ``Ljava/lang/String;`` in the DEX."""
    context = _context()

    assert match_type_rank(parse_java_type("String"), "Ljava/lang/String;", context) is not None
    assert match_type_rank(parse_java_type("int"), "I", context) is not None


def test_a_simple_name_does_not_match_a_class_in_another_package() -> None:
    """``Alias`` means the class in this package, not one somewhere else.

    The source did not say which package the class came from — but the file's
    own package is part of what it said, and a class in another package has to
    be written out or imported.
    """
    context = _context()

    assert match_type_rank(parse_java_type("Alias"), LOCAL_ALIAS_TYPE, context) is not None
    assert match_type_rank(parse_java_type("Alias"), REMOTE_ALIAS_TYPE, context) is None


def test_a_qualified_name_matches_the_class_it_writes_out() -> None:
    """A name the source wrote out in full is believed exactly."""
    context = _context()

    assert (
        match_type_rank(parse_java_type("com.example.demo.other.Alias"), REMOTE_ALIAS_TYPE, context)
        is not None
    )
    assert (
        match_type_rank(parse_java_type("com.example.demo.other.Alias"), LOCAL_ALIAS_TYPE, context)
        is None
    )


def test_a_generic_type_is_matched_by_its_erasure() -> None:
    """``List<String>`` is a ``List``: the generics say nothing more."""
    context = _context()

    assert match_type_rank(parse_java_type("List<String>"), "Ljava/util/List;", context) is not None


def test_an_array_is_matched_by_its_dimensions() -> None:
    """``String[]`` is one dimension, and the descriptor says so too."""
    context = _context()

    assert match_type_rank(parse_java_type("String[]"), "[Ljava/lang/String;", context) is not None
    assert match_type_rank(parse_java_type("String[]"), "Ljava/lang/String;", context) is None


def test_a_varargs_parameter_is_an_array() -> None:
    """``String...`` is the array a varargs parameter is."""
    context = _context()

    assert match_type_rank(parse_java_type("String..."), "[Ljava/lang/String;", context) is not None


def test_a_primitive_is_matched_by_its_own_letter() -> None:
    """``int`` is ``I``, and a primitive is never a class."""
    context = _context()

    assert match_type_rank(parse_java_type("int"), "I", context) is not None
    assert match_type_rank(parse_java_type("int"), "Ljava/lang/Integer;", context) is None


def test_a_type_the_decompiler_could_not_work_out_matches_any_type() -> None:
    """``var1`` says nothing, so it decides nothing."""
    context = _context()

    rank = match_type_rank(parse_java_type("var1"), "Ljava/lang/String;", context)

    assert rank is not None
    assert rank > 0, "an unknown type must not outrank a type the source spelled out"


def test_a_parameter_list_is_matched_as_a_whole() -> None:
    """The list has to have the arity the descriptor has."""
    context = _context()

    assert match_parameter_rank(["String", "String"], SIGN_TWO, context) is not None
    assert match_parameter_rank(["String"], SIGN_TWO, context) is None


def test_the_parameter_list_of_a_declaration_is_read_off_the_source() -> None:
    """The types are what the source wrote, and nothing else."""
    from dexatlas.core.methods import parse_parameter_types

    assert parse_parameter_types("String str") == ("String",)
    assert parse_parameter_types("String str, String str2") == ("String", "String")
    assert parse_parameter_types("int i, String str") == ("int", "String")
    assert parse_parameter_types("final String str") == ("String",)
    assert parse_parameter_types("List<String> list") == ("List<String>",)
    assert parse_parameter_types("") == ()


def test_an_opaque_parameter_is_not_a_type() -> None:
    """``var1`` is a name the decompiler invented, not a class."""
    opaque = parse_java_type("var1")
    known = parse_java_type("String")

    assert not opaque.known
    assert known.known


# -- the document says which method it holds -----------------------------------


def test_the_document_says_which_overload_it_holds(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """A name-only request still says which of the overloads it got.

    The index knows the descriptor even when the caller did not ask with one,
    and a document that says only the name leaves the reader guessing which
    of the overloads is in front of them.
    """
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    document = analyzer.method_source_document(project_id, CLASS_NAME, "digest")

    assert document is not None
    assert document.descriptor == SIGN_ONE


def test_the_locator_names_the_method_not_just_its_name(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """Two overloads share a name, and a locator that named only the name
    would point at both of them."""
    workspace, project_id = workspace_with_sources
    analyzer = _analyzer(workspace)

    document = analyzer.method_source_document(project_id, CLASS_NAME, "sign", SIGN_TWO)

    assert document is not None
    assert document.provenance[0].locator.endswith(f"#sign{SIGN_TWO}")


# -- the CLI ------------------------------------------------------------------


def _run_cli(*args: str):
    from typer.testing import CliRunner

    from dexatlas.cli.main import app as cli

    return CliRunner().invoke(cli, list(args))


def test_the_cli_reports_an_ambiguous_method(
    workspace_with_sources: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exit code says "ask again", not "there is nothing there"."""
    workspace, project_id = workspace_with_sources
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(workspace))
    get_settings.cache_clear()
    try:
        result = _run_cli("source", project_id, CLASS_NAME, "--method", "sign")
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 4
    assert "Ambiguous" in result.stderr
    assert SIGN_ONE in result.stderr
    assert SIGN_TWO in result.stderr
    # Nothing was printed to stdout: there is no source to print.
    assert result.stdout.strip() == ""


def test_the_cli_answers_a_descriptor(
    workspace_with_sources: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace, project_id = workspace_with_sources
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(workspace))
    get_settings.cache_clear()
    try:
        result = _run_cli(
            "source",
            project_id,
            CLASS_NAME,
            "--method",
            "sign",
            "--descriptor",
            SIGN_ONE,
        )
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0
    assert "String sign(String str)" in result.stdout


def test_the_cli_answers_a_name_that_is_not_ambiguous(
    workspace_with_sources: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ordinary case keeps its exit code."""
    workspace, project_id = workspace_with_sources
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(workspace))
    get_settings.cache_clear()
    try:
        result = _run_cli("source", project_id, CLASS_NAME, "--method", "digest")
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0
    assert "String digest(String str)" in result.stdout


def test_the_cli_refuses_a_descriptor_that_is_not_one(
    workspace_with_sources: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A wrong request is exit code 2, not an empty answer."""
    workspace, project_id = workspace_with_sources
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(workspace))
    get_settings.cache_clear()
    try:
        result = _run_cli(
            "source",
            project_id,
            CLASS_NAME,
            "--method",
            "sign",
            "--descriptor",
            "sign",
        )
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 2
    assert "descriptor" in result.stderr.lower()


# -- the API ------------------------------------------------------------------


def _client_for(workspace: Path) -> TestClient:
    settings = Settings(workspace=workspace)
    settings.ensure_workspace()
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_the_api_reports_an_ambiguous_method(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """409, with the candidates, so the caller can ask again."""
    workspace, project_id = workspace_with_sources

    with _client_for(workspace) as client:
        response = client.get(f"/projects/{project_id}/methods/{CLASS_NAME}/sign")

    app.dependency_overrides.clear()
    assert response.status_code == 409
    body = response.json()
    assert {candidate["descriptor"] for candidate in body["candidates"]} == {
        SIGN_INT,
        SIGN_ONE,
        SIGN_TWO,
    }
    assert body["method"] == "sign"


def test_the_api_answers_a_descriptor(workspace_with_sources: tuple[Path, str]) -> None:
    workspace, project_id = workspace_with_sources

    with _client_for(workspace) as client:
        response = client.get(
            f"/projects/{project_id}/methods/{CLASS_NAME}/sign",
            params={"descriptor": SIGN_ONE},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert "String sign(String str)" in response.text


def test_the_api_refuses_a_descriptor_that_is_not_one(
    workspace_with_sources: tuple[Path, str],
) -> None:
    workspace, project_id = workspace_with_sources

    with _client_for(workspace) as client:
        response = client.get(
            f"/projects/{project_id}/methods/{CLASS_NAME}/sign",
            params={"descriptor": "sign"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 400


def test_the_api_document_carries_the_descriptor(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """A document that says which overload it holds is worth more than one
    that says only the name."""
    workspace, project_id = workspace_with_sources

    with _client_for(workspace) as client:
        response = client.get(
            f"/projects/{project_id}/methods/{CLASS_NAME}/sign",
            params={"descriptor": SIGN_ONE, "format": "json"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["descriptor"] == SIGN_ONE
    assert body["method"] == "sign"


# -- the interface itself -----------------------------------------------------


def test_a_descriptor_that_is_not_one_is_refused() -> None:
    assert is_descriptor(SIGN_ONE)
    assert is_descriptor(NO_ARGS)
    assert is_descriptor("(Ljava/lang/String;)V")
    assert not is_descriptor("sign")
    assert not is_descriptor("(Ljava/lang/String;)")
    assert not is_descriptor("")


def test_the_json_document_of_the_cli_carries_the_descriptor(
    workspace_with_sources: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace, project_id = workspace_with_sources
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(workspace))
    get_settings.cache_clear()
    try:
        result = _run_cli(
            "source",
            project_id,
            CLASS_NAME,
            "--method",
            "sign",
            "--descriptor",
            SIGN_TWO,
            "--format",
            "json",
        )
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["descriptor"] == SIGN_TWO


# -- the whole thing, against a real decompiler -------------------------------

#: The smali of the class the end-to-end test analyses. Two overloads of one
#: name, a constructor, and a method of the class's own name.
OVERLOAD_SMALI = """.class public final Lcom/example/overload/Crypto;
.super Ljava/lang/Object;
.source "Crypto.java"

.method public constructor <init>()V
    .locals 0

    invoke-static {}, Lcom/example/overload/Crypto;->seed()V

    return-void
.end method

.method public static Crypto()V
    .locals 0

    return-void
.end method

.method public static seed()V
    .locals 0

    return-void
.end method

.method public static sign(Ljava/lang/String;)Ljava/lang/String;
    .locals 1

    return-object p0
.end method

.method public static sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;
    .locals 1

    new-instance v0, Ljava/lang/StringBuilder;

    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v0, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    return-object v0
.end method
"""

OVERLOAD_MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.overload" android:versionCode="1" android:versionName="1.0">
    <uses-sdk android:minSdkVersion="24" android:targetSdkVersion="34" />
    <application android:label="Overload" />
</manifest>
"""

APKTOOL_YML = """version: 3.0.3
apkFileName: overload.apk
isFrameworkApk: false
usesFramework:
  ids:
  - 1
sdkInfo:
  minSdkVersion: 24
  targetSdkVersion: 34
packageInfo:
  renameManifestPackage: null
sharedLibrary: false
sparseResources: false
unknownFiles:
  dirs: []
  files: []
doNotCompress:
- resources.arsc
versionInfo:
  versionCode: 1
  versionName: 1.0
"""

OVERLOAD_CLASS = "com.example.overload.Crypto"
OVERLOAD_SIGN_ONE = "(Ljava/lang/String;)Ljava/lang/String;"
OVERLOAD_SIGN_TWO = "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"


def _apktool_argv(settings: Settings, *args: str) -> list[str] | None:
    """The command line that runs Apktool, whichever way it is installed."""
    resolved = ApktoolBackend(settings).resolve()
    if resolved is None:
        return None
    if resolved.suffix == ".jar":
        return ["java", "-jar", str(resolved), *args]
    return [str(resolved), *args]


@pytest.fixture(scope="module")
def analysed_overload_apk(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    """Build an APK with overloads, analyse it, and share the result.

    The APK is built from smali by Apktool, so the bytes are the project's
    own and the test does not depend on a third-party sample. The class it
    holds has two overloads of one name, so a decompiler that matched on the
    name would return the same body for both requests.
    """
    settings = Settings()
    argv = _apktool_argv(settings, "b")
    if argv is None:
        pytest.skip("apktool not installed")

    root = tmp_path_factory.mktemp("overload-apk")
    project = root / "project"
    smali = project / "smali" / "com" / "example" / "overload"
    smali.mkdir(parents=True)
    (smali / "Crypto.smali").write_text(OVERLOAD_SMALI, encoding="utf-8")
    (project / "AndroidManifest.xml").write_text(OVERLOAD_MANIFEST, encoding="utf-8")
    (project / "apktool.yml").write_text(APKTOOL_YML, encoding="utf-8")

    apk = root / "overload.apk"
    build = subprocess.run(
        [*argv, str(project), "-o", str(apk)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if build.returncode != 0 or not apk.is_file():
        pytest.skip(f"apktool could not build the fixture: {build.stderr[-400:]}")

    workspace = tmp_path_factory.mktemp("overload-workspace")
    analyzer = Analyzer(Settings(workspace=workspace))
    result = analyzer.analyze(apk)

    return {
        "analyzer": analyzer,
        "project_id": result.project.id,
    }


@pytest.mark.slow
@pytest.mark.skipif(not androguard_available(), reason="androguard not installed")
@pytest.mark.skipif(JadxBackend(Settings()).resolve() is None, reason="jadx not installed")
def test_the_real_decompiler_output_resolves_every_overload(
    analysed_overload_apk: dict[str, object],
) -> None:
    """The end to end: the real JADX output, and the real symbol index.

    The Java in this file is the Java a decompiler writes, with the methods in
    the order it writes them and the parameters named the way it names them.
    """
    analyzer: Analyzer = analysed_overload_apk["analyzer"]  # type: ignore[assignment]
    project_id: str = analysed_overload_apk["project_id"]  # type: ignore[assignment]

    one = analyzer.method_source_document(project_id, OVERLOAD_CLASS, "sign", OVERLOAD_SIGN_ONE)
    two = analyzer.method_source_document(project_id, OVERLOAD_CLASS, "sign", OVERLOAD_SIGN_TWO)

    assert one is not None
    assert one.text.count("sign(") == 1
    assert "sign(String str)" in one.text
    assert "sign(String str, String str2)" not in one.text

    assert two is not None
    assert "sign(String str, String str2)" in two.text


@pytest.mark.slow
@pytest.mark.skipif(not androguard_available(), reason="androguard not installed")
def test_the_real_decompiler_output_reports_an_ambiguous_name(
    analysed_overload_apk: dict[str, object],
) -> None:
    """Two overloads, one name, and no descriptor to say which."""
    analyzer: Analyzer = analysed_overload_apk["analyzer"]  # type: ignore[assignment]
    project_id: str = analysed_overload_apk["project_id"]  # type: ignore[assignment]

    with pytest.raises(AmbiguousMethodError) as caught:
        analyzer.method_source_document(project_id, OVERLOAD_CLASS, "sign")

    assert {candidate.descriptor for candidate in caught.value.candidates} == {
        OVERLOAD_SIGN_ONE,
        OVERLOAD_SIGN_TWO,
    }
