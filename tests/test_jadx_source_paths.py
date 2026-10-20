"""A class name that is not a class name.

The JADX backend turns a class name into a path to read. That name arrives from
an HTTP request or from an analysed APK, so it is untrusted input, and a name
that is joined onto the output directory without a guard walks straight out of
the tree — and reads a file that has nothing to do with the analysis.

These tests attack the real flows: the REST endpoint and the CLI command that
a caller actually uses. The unit-level checks below them pin the rule the two
flows share.
"""

from __future__ import annotations

import json
import os
import urllib.parse
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dexatlas.api.app import app
from dexatlas.config.settings import Settings, get_settings
from dexatlas.core.models import ApkMetadata, Project, ProjectStatus
from dexatlas.core.storage import Store
from dexatlas.tools.jadx.adapter import JadxBackend

FAKE_SHA256 = "d" * 64

CLASS_NAME = "com.example.demo.Crypto"

JAVA_SOURCE = """package com.example.demo;

public class Crypto {
    public static String sign(String a, String b) {
        return a + b;
    }
}
"""

#: The secret the attack is after: a file outside the analysis tree, whose
#: contents must never reach a caller.
SECRET = "THIS-FILE-IS-NOT-PART-OF-THE-ANALYSIS"

#: The names that are not class names, and the reason each one is here.
#:
#: The first eight are the Smali suite's cases at the same specification: a
#: name that is already a path must not be honoured as one. The rest are the
#: cases a path built out of a class name has on its own.
#:
#: ``{absolute}`` is a path to a file that really exists — see the ``secret``
#: fixture. A name that is refused because the file it names is not there
#: proves nothing.
HOSTILE_NAMES = [
    ("traversal", "../../../../etc/passwd"),
    ("windows-traversal", "..\\..\\..\\windows\\win.ini"),
    ("dot-dot", ".."),
    ("dot", "."),
    ("nul", "com.foo." + chr(0) + "Bar"),
    ("dots", "....//....//etc/passwd"),
    ("rooted", "/etc/passwd"),
    ("slash", "com.foo/../../secret"),
    ("empty-segment", "com..foo.Bar"),
    ("encoded-traversal", "com.foo..%2f..%2fetc%2fpasswd"),
    ("absolute", "{absolute}"),
    ("absolute-forward-slashes", "{absolute_forward}"),
    ("unc", "\\\\server\\share\\secret\\loot.java"),
    ("drive-relative", "C:secret\\loot.java"),
    ("encoded-slash", "com.foo%2f..%2f..%2fsecret"),
    ("control", "com.foo." + chr(7) + "Bar"),
    ("star", "com.foo.*"),
    ("question", "com.foo?"),
    ("bracket", "com.foo[0]"),
    ("too-long", "com." + "a" * 5000 + ".Bar"),
    ("ideographic-dot", "com.example。Crypto"),
    ("cyrillic-a", "com.exаmple.Crypto"),  # noqa: RUF001
]

HOSTILE_IDS = [name for name, _ in HOSTILE_NAMES]


def _absolute_name(tmp_path: Path) -> str:
    """The name the absolute-path attack uses."""
    return f"{tmp_path}{os.sep}secret{os.sep}loot"


def _hostile_name(name_id: str, tmp_path: Path) -> str:
    """The hostile name, with the absolute path substituted in."""
    template = dict(HOSTILE_NAMES)[name_id]
    absolute = _absolute_name(tmp_path)
    return template.format(absolute=absolute, absolute_forward=absolute.replace("\\", "/"))


def _old_join(name: str, sources: Path) -> Path:
    """Where the old, unguarded join would have looked.

    The old code replaced every dot with a slash before joining the name onto
    the output directory, so a name that spelled out a file did not reach
    that file — it reached a different one. This is the join that reached
    files.
    """
    return sources / Path(name.replace(".", "/") + ".java")


@pytest.fixture
def secret(tmp_path: Path) -> Iterator[Path]:
    """A file outside the analysis tree, holding the secret.

    It is placed exactly where the old, unguarded join would have looked, so
    the attack is live rather than hypothetical: a name that is refused
    because the file it names is not there would prove nothing at all.
    """
    sources = tmp_path / "jadx" / "sources"
    target = _old_join(_absolute_name(tmp_path), sources)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(SECRET, encoding="utf-8")
    yield target
    target.unlink(missing_ok=True)


@pytest.fixture
def workspace_with_sources(tmp_path: Path) -> tuple[Path, str]:
    """A workspace holding one class's Java, and its project row."""
    workspace = tmp_path / "workspace"
    project_id = Project.new_id(FAKE_SHA256)
    project_dir = workspace / "projects" / project_id

    java = project_dir / "jadx" / "sources" / "com" / "example" / "demo" / "Crypto.java"
    java.parent.mkdir(parents=True)
    java.write_text(JAVA_SOURCE, encoding="utf-8")

    store = Store.open(workspace / "dexatlas.db")
    store.save_project(
        Project(
            id=project_id,
            apk=ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=Path("demo.apk")),
            status=ProjectStatus.COMPLETED,
            tool_versions={"jadx": "1.5.2"},
        ),
        project_dir,
        manifest=None,
    )
    return workspace, project_id


@pytest.fixture
def jadx_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the decompiler answer, without running it."""
    monkeypatch.setattr(JadxBackend, "resolve", lambda self: Path("jadx-stub"))


@pytest.fixture
def read_probe(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """Every file the JADX backend is asked to read.

    The attack is not "the endpoint returned something odd" — it is "a file
    outside the analysis tree was opened". This records the opens, so the test
    can say that no such open happened.
    """
    from dexatlas.tools.jadx import adapter

    opened: list[Path] = []
    original = adapter.read_text

    def spy(path: Path) -> str | None:
        opened.append(path)
        return original(path)

    monkeypatch.setattr(adapter, "read_text", spy)
    return opened


def _client_for(workspace: Path) -> TestClient:
    settings = Settings(workspace=workspace)
    settings.ensure_workspace()
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def _sources_of(workspace: Path, project_id: str) -> Path:
    return (workspace / "projects" / project_id / "jadx" / "sources").resolve()


# -- the rule ----------------------------------------------------------------


@pytest.mark.parametrize("name_id", HOSTILE_IDS)
def test_a_hostile_class_name_resolves_to_nothing_outside_the_tree(
    jadx: JadxBackend, tmp_path: Path, secret: Path, name_id: str
) -> None:
    """Resolution must either stay inside the output tree or return None.

    The name is untrusted input, so the rule is not "the path looks sane" but
    "the path is inside the tree, or there is no path".
    """
    output = tmp_path / "jadx"
    sources = output / "sources"
    java = sources / "com" / "example" / "demo" / "Crypto.java"
    java.parent.mkdir(parents=True)
    java.write_text(JAVA_SOURCE, encoding="utf-8")

    hostile = _hostile_name(name_id, tmp_path)
    found = jadx.class_source_path(hostile, output)

    if found is None:
        return
    resolved = found.resolve()
    assert resolved.is_relative_to(sources.resolve()), (
        f"{hostile!r} resolved outside the output directory: {resolved}"
    )


@pytest.mark.parametrize("name_id", HOSTILE_IDS)
def test_a_hostile_class_name_reads_no_file(
    jadx: JadxBackend, tmp_path: Path, secret: Path, name_id: str
) -> None:
    """The read is the damage. A name that resolves to nothing reads nothing."""
    output = tmp_path / "jadx"
    sources = output / "sources"
    java = sources / "com" / "example" / "demo" / "Crypto.java"
    java.parent.mkdir(parents=True)
    java.write_text(JAVA_SOURCE, encoding="utf-8")

    hostile = _hostile_name(name_id, tmp_path)

    assert jadx.read_class_source(hostile, output) is None


def test_an_absolute_class_name_cannot_read_an_absolute_path(
    jadx: JadxBackend, tmp_path: Path, secret: Path
) -> None:
    """The case that leaked: an absolute path is honoured as a path by pathlib.

    ``sources / Path("C:/...")`` is that absolute path, not a path inside the
    tree — so the file it names really is opened.
    """
    output = tmp_path / "jadx"
    (output / "sources").mkdir(parents=True)
    hostile = _hostile_name("absolute", tmp_path)

    assert jadx.class_source_path(hostile, output) is None
    assert jadx.read_class_source(hostile, output) is None


def test_a_valid_class_name_still_resolves(jadx: JadxBackend, tmp_path: Path) -> None:
    """The guard must not stop the ordinary case."""
    output = tmp_path / "jadx"
    java = output / "sources" / "com" / "example" / "demo" / "Crypto.java"
    java.parent.mkdir(parents=True)
    java.write_text(JAVA_SOURCE, encoding="utf-8")

    found = jadx.class_source_path(CLASS_NAME, output)

    assert found == java


def test_a_nested_class_still_resolves_to_its_outer_file(jadx: JadxBackend, tmp_path: Path) -> None:
    """A nested class shares its outer class's file — that must keep working."""
    output = tmp_path / "jadx"
    java = output / "sources" / "com" / "example" / "demo" / "Crypto.java"
    java.parent.mkdir(parents=True)
    java.write_text(JAVA_SOURCE, encoding="utf-8")

    found = jadx.class_source_path(f"{CLASS_NAME}$Helper", output)

    assert found == java


def test_a_link_out_of_the_tree_is_not_followed(jadx: JadxBackend, tmp_path: Path) -> None:
    """The name was checked; the file could still be a link out of the tree.

    This is the belt to the braces. A file inside the output tree that points
    somewhere else would otherwise be read like a file of the analysis.
    """
    secret = tmp_path / "outside.secret"
    secret.write_text(SECRET, encoding="utf-8")

    sources = tmp_path / "jadx" / "sources" / "com" / "example" / "demo"
    sources.mkdir(parents=True)
    link = sources / "Crypto.java"
    try:
        link.symlink_to(secret)
    except (OSError, NotImplementedError):
        pytest.skip("this platform cannot make a symbolic link")

    assert jadx.class_source_path(CLASS_NAME, tmp_path / "jadx") is None


# -- the REST endpoint -------------------------------------------------------


def test_the_api_answers_a_traversal_with_not_found(
    workspace_with_sources: tuple[Path, str],
    tmp_path: Path,
    secret: Path,
    jadx_available: None,
    read_probe: list[Path],
) -> None:
    """A name that tries to leave the tree is a name that does not exist.

    It must not be a 500: a hostile input is not an unhandled exception, and
    the server's filesystem layout must not end up in an error page.
    """
    workspace, project_id = workspace_with_sources
    hostile = _hostile_name("absolute", tmp_path)

    with _client_for(workspace) as client:
        response = client.get(
            f"/projects/{project_id}/classes/{urllib.parse.quote(hostile, safe='')}/source"
        )

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert "Traceback" not in response.text
    assert str(workspace) not in response.text
    assert SECRET not in response.text


@pytest.mark.parametrize("name_id", HOSTILE_IDS)
def test_the_api_opens_no_file_outside_the_tree(
    workspace_with_sources: tuple[Path, str],
    tmp_path: Path,
    secret: Path,
    jadx_available: None,
    read_probe: list[Path],
    name_id: str,
) -> None:
    """The proof that the attack fails: nothing outside the tree was opened."""
    workspace, project_id = workspace_with_sources
    sources = _sources_of(workspace, project_id)
    hostile = _hostile_name(name_id, tmp_path)

    with _client_for(workspace) as client:
        response = client.get(
            f"/projects/{project_id}/classes/{urllib.parse.quote(hostile, safe='')}/source"
        )

    app.dependency_overrides.clear()

    assert response.status_code == 404
    outside = [path for path in read_probe if not path.resolve().is_relative_to(sources)]
    assert not outside, f"the endpoint opened files outside the analysis tree: {outside!r}"
    assert SECRET not in response.text


def test_the_api_returns_the_real_class_when_the_name_is_real(
    workspace_with_sources: tuple[Path, str],
    jadx_available: None,
    read_probe: list[Path],
) -> None:
    """The other half of the contract: a real class is still served."""
    workspace, project_id = workspace_with_sources

    with _client_for(workspace) as client:
        response = client.get(f"/projects/{project_id}/classes/{CLASS_NAME}/source")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "public class Crypto" in response.text
    assert response.headers["X-DexAtlas-Source-Kind"] == "java"


# -- the CLI -----------------------------------------------------------------


def _run_cli(*args: str):
    from typer.testing import CliRunner

    from dexatlas.cli.main import app as cli

    return CliRunner().invoke(cli, list(args))


@pytest.mark.parametrize("name_id", HOSTILE_IDS)
def test_the_cli_reports_no_match_for_a_traversal(
    workspace_with_sources: tuple[Path, str],
    tmp_path: Path,
    secret: Path,
    jadx_available: None,
    read_probe: list[Path],
    monkeypatch: pytest.MonkeyPatch,
    name_id: str,
) -> None:
    """The CLI must say "no match", not print a traceback with a server path."""
    workspace, project_id = workspace_with_sources
    hostile = _hostile_name(name_id, tmp_path)
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(workspace))
    get_settings.cache_clear()
    try:
        result = _run_cli("source", project_id, hostile)
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 1
    assert "No source for" in result.output
    assert "Traceback" not in result.output
    assert str(workspace) not in result.output
    assert SECRET not in result.output

    sources = _sources_of(workspace, project_id)
    outside = [path for path in read_probe if not path.resolve().is_relative_to(sources)]
    assert not outside, f"the command opened files outside the analysis tree: {outside!r}"


def test_the_cli_still_prints_a_real_class(
    workspace_with_sources: tuple[Path, str],
    jadx_available: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, project_id = workspace_with_sources
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(workspace))
    get_settings.cache_clear()
    try:
        result = _run_cli("source", project_id, CLASS_NAME)
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0
    assert "public class Crypto" in result.stdout


# -- the schema --------------------------------------------------------------


def test_the_openapi_schema_says_what_the_source_endpoint_returns(
    workspace_with_sources: tuple[Path, str],
) -> None:
    """A client generated from the schema has to know what it will get.

    The endpoint answers with the source text by default and with a JSON
    document on request, and both carry headers the schema did not mention.
    """
    workspace, _project_id = workspace_with_sources

    with _client_for(workspace) as client:
        schema = client.get("/openapi.json").json()

    app.dependency_overrides.clear()

    operation = schema["paths"]["/projects/{project_id}/classes/{class_name}/source"]["get"]
    content = operation["responses"]["200"]["content"]

    assert "text/plain" in content
    assert "application/json" in content

    headers = operation["responses"]["200"]["headers"]
    for header in (
        "X-DexAtlas-Source-Kind",
        "X-DexAtlas-Source-Tool",
        "X-DexAtlas-Source-Locator",
        "X-DexAtlas-Source-Tool-Version",
    ):
        assert header in headers, f"the schema does not declare {header}"

    properties = content["application/json"]["schema"]["properties"]
    assert set(properties) == {"project_id", "class_name", "method", "kind", "provenance", "text"}


def test_the_json_form_is_the_one_the_schema_describes(
    workspace_with_sources: tuple[Path, str],
    jadx_available: None,
) -> None:
    """The declared JSON shape has to be the JSON that comes back."""
    workspace, project_id = workspace_with_sources

    with _client_for(workspace) as client:
        response = client.get(
            f"/projects/{project_id}/classes/{CLASS_NAME}/source", params={"format": "json"}
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = json.loads(response.text)
    assert set(body) == {"project_id", "class_name", "method", "kind", "provenance", "text"}
    assert body["kind"] == "java"
    assert body["provenance"][0]["tool"] == "jadx"
