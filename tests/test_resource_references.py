"""The references between resources, read out of Apktool's decoded ``res/`` tree.

A layout that says ``android:text="@string/app_name"`` does not name a text —
it points at one. The layout-text index holds what is written; this index
holds what is *referred to*, so the question "which layouts use this string?"
has an answer with a place attached to it.

The parsing tests write their own ``res/`` tree, so they do not depend on
which backends the machine happens to have. The storage and retrieval tests
write the rows straight into a store, the way the pipeline would.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dexatlas.api.app import app
from dexatlas.config.settings import Settings, get_settings
from dexatlas.core.models import (
    ApkMetadata,
    Project,
    Provenance,
    ResourceReference,
)
from dexatlas.core.storage import Store
from dexatlas.tools.apktool.adapter import ApktoolBackend

#: A SHA-256 that is obviously a placeholder but has the right shape.
FAKE_SHA256 = "a" * 64


def _res_file(output_dir: Path, relative: str, body: str) -> Path:
    """Write one file into the decoded ``res/`` tree."""
    path = output_dir / "res" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


#: A layout whose text is a reference, not a literal. The TextView starts on
#: line 5, the EditText on line 9.
REFERENCING_LAYOUT = """<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent">
    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="@string/app_name" />
    <EditText
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:hint="@string/greeting" />
</LinearLayout>
"""


# -- reading the references out of the tree ----------------------------------


def test_a_string_reference_in_a_layout_is_found(apktool: ApktoolBackend, tmp_path: Path) -> None:
    """``android:text="@string/app_name"`` is a reference to a declaration
    somewhere else. It is read as an edge: the layout that points, and the
    resource it points at."""
    _res_file(tmp_path, "layout/activity_main.xml", REFERENCING_LAYOUT)

    rows, errors = apktool.read_resource_references(tmp_path, FAKE_SHA256)

    assert errors == []
    assert [(row.res_type, row.res_name, row.attribute) for row in rows] == [
        ("string", "app_name", "text"),
        ("string", "greeting", "hint"),
    ]


def test_a_reference_row_points_at_its_file_and_line(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    """The provenance lands the reader on the element that carries the
    reference: the file it was decoded from, and where in that file the
    element starts."""
    _res_file(tmp_path, "layout/activity_main.xml", REFERENCING_LAYOUT)

    rows, _ = apktool.read_resource_references(tmp_path, FAKE_SHA256)

    text_row = rows[0]
    assert text_row.file == "res/layout/activity_main.xml"
    assert text_row.element == "TextView"
    assert text_row.line == 5
    assert text_row.provenance[0].tool == "apktool"
    assert text_row.provenance[0].apk_sha256 == FAKE_SHA256
    assert text_row.provenance[0].locator == (
        "apktool:res/layout/activity_main.xml#line=5;TextView"
    )


def test_a_platform_reference_keeps_its_android_package(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    """``@android:string/ok`` names the platform's string, not the APK's.
    The package is part of what the reference names."""
    _res_file(
        tmp_path,
        "layout/platform.xml",
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<TextView xmlns:android="http://schemas.android.com/apk/res/android"\n'
        '    android:text="@android:string/ok" />\n',
    )

    rows, errors = apktool.read_resource_references(tmp_path, FAKE_SHA256)

    assert errors == []
    assert len(rows) == 1
    assert rows[0].package == "android"
    assert rows[0].res_type == "string"
    assert rows[0].res_name == "ok"
    assert rows[0].reference == "@android:string/ok"


def test_an_unqualified_reference_has_no_package(apktool: ApktoolBackend, tmp_path: Path) -> None:
    """``@string/app_name`` names this APK's own ``string/app_name``."""
    _res_file(
        tmp_path,
        "xml/shortcuts.xml",
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<shortcuts xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <shortcut android:shortcutId="main" android:enabled="true"\n'
        '        android:icon="@mipmap/ic_launcher" android:label="@string/app_name" />\n'
        "</shortcuts>\n",
    )

    rows, errors = apktool.read_resource_references(tmp_path, FAKE_SHA256)

    assert errors == []
    assert [(row.res_type, row.res_name, row.attribute) for row in rows] == [
        ("mipmap", "ic_launcher", "icon"),
        ("string", "app_name", "label"),
    ]
    assert all(row.package is None for row in rows)


def test_values_that_are_not_references_are_not_rows(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    """A literal, an ``@+id/`` definition and an ``?attr/`` lookup are not
    references to a resource declaration, and none of them is a row."""
    _res_file(
        tmp_path,
        "layout/mixed.xml",
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"\n'
        '    android:orientation="?attr/orientation"\n'
        '    android:id="@+id/container">\n'
        '    <TextView android:text="Just words" />\n'
        "</LinearLayout>\n",
    )

    rows, errors = apktool.read_resource_references(tmp_path, FAKE_SHA256)

    assert errors == []
    assert rows == []


def test_an_id_reference_is_a_row_and_a_definition_is_not(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    """``@id/text_view`` points at an id declared elsewhere, so it is a
    reference; ``@+id/container`` *is* the declaration, so it is not."""
    _res_file(
        tmp_path,
        "layout/ids.xml",
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"\n'
        '    android:id="@+id/container">\n'
        '    <TextView android:id="@id/text_view" />\n'
        "</LinearLayout>\n",
    )

    rows, errors = apktool.read_resource_references(tmp_path, FAKE_SHA256)

    assert errors == []
    assert [(row.res_type, row.res_name, row.attribute) for row in rows] == [
        ("id", "text_view", "id")
    ]


def test_a_reference_in_the_values_directory_is_read_too(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    """A values file can refer to another resource — a style whose parent is
    written as ``@style/`` — and the scan is of the whole tree, not only the
    layouts."""
    _res_file(
        tmp_path,
        "values/styles.xml",
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<resources>\n"
        '    <style name="AppTheme" parent="@style/Theme.Material">\n'
        '        <item name="android:textColor">@color/ink</item>\n'
        "    </style>\n"
        "</resources>\n",
    )

    rows, errors = apktool.read_resource_references(tmp_path, FAKE_SHA256)

    assert errors == []
    assert [(row.res_type, row.res_name, row.attribute) for row in rows] == [
        ("style", "Theme.Material", "parent"),
        ("color", "ink", "android:textColor"),
    ]


def test_a_broken_file_is_an_error_and_the_rest_are_still_read(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    """One file that will not parse is one error, and the references around
    it are still read — the same bargain the declarations strike."""
    _res_file(tmp_path, "layout/broken.xml", "<LinearLayout><TextView")
    _res_file(tmp_path, "layout/fine.xml", REFERENCING_LAYOUT)

    rows, errors = apktool.read_resource_references(tmp_path, FAKE_SHA256)

    assert len(errors) == 1
    assert "res/layout/broken.xml" in errors[0].message
    assert len(rows) == 2


def test_an_apk_without_a_resource_tree_yields_no_references(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    _res_file(tmp_path, "placeholder.txt", "not xml")

    rows, errors = apktool.read_resource_references(tmp_path, FAKE_SHA256)

    assert rows == []
    assert errors == []


def test_an_entity_declaration_is_refused(apktool: ApktoolBackend, tmp_path: Path) -> None:
    """The references are read out of the same untrusted tree as the
    declarations, so the same safe parser stands in front of them."""
    _res_file(
        tmp_path,
        "layout/hostile.xml",
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>\n'
        '<TextView android:text="&xxe;" xmlns:android="http://schemas.android.com/apk/res/android"/>\n',
    )

    rows, errors = apktool.read_resource_references(tmp_path, FAKE_SHA256)

    assert rows == []
    assert len(errors) == 1
    assert "res/layout/hostile.xml" in errors[0].message


# -- storage -----------------------------------------------------------------


def _reference(
    res_type: str = "string",
    res_name: str = "app_name",
    file: str = "res/layout/activity_main.xml",
    line: int = 5,
    attribute: str = "text",
) -> ResourceReference:
    return ResourceReference(
        reference=f"@{res_type}/{res_name}",
        res_type=res_type,
        res_name=res_name,
        attribute=attribute,
        element="TextView",
        line=line,
        file=file,
        provenance=[
            Provenance(
                tool="apktool",
                tool_version="2.11.1",
                apk_sha256=FAKE_SHA256,
                locator=f"apktool:{file}#line={line};TextView",
            )
        ],
    )


def test_a_reference_survives_the_database(store: Store, tmp_path: Path) -> None:
    """The whole path: read out of the tree, then written to the database,
    then read back with its locator intact."""
    project = Project.create(
        ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=tmp_path / "demo.apk")
    )
    store.save_project(project, tmp_path / "workspace", manifest=None)

    rows, errors = apktool_rows(tmp_path)
    assert errors == []
    counts = store.save_symbols(project.id, [], [], [], [], [], [], resource_references=rows)

    assert counts.resource_references == 2
    stored = store.list_resource_references(project.id)
    assert [(row.res_type, row.res_name) for row in stored] == [
        ("string", "app_name"),
        ("string", "greeting"),
    ]
    assert stored[0].file == "res/layout/activity_main.xml"
    assert stored[0].provenance[0].locator == (
        "apktool:res/layout/activity_main.xml#line=5;TextView"
    )


def apktool_rows(tmp_path: Path) -> tuple[list[ResourceReference], list]:
    """The references of the standard layout, read the way the backend reads them."""
    _res_file(tmp_path, "layout/activity_main.xml", REFERENCING_LAYOUT)
    return ApktoolBackend(Settings()).read_resource_references(tmp_path, FAKE_SHA256)


def test_references_are_looked_up_by_the_resource_they_name(store: Store, tmp_path: Path) -> None:
    """\"Who references ``string/app_name``?\" is the question the index
    exists to answer, so the lookup is by the resource, not only by row."""
    project = Project.create(
        ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=tmp_path / "demo.apk")
    )
    store.save_project(project, tmp_path / "workspace", manifest=None)
    store.save_symbols(
        project.id,
        [],
        [],
        [],
        [],
        [],
        [],
        resource_references=[
            _reference(res_type="string", res_name="app_name", file="res/layout/a.xml"),
            _reference(res_type="string", res_name="app_name", file="res/layout/b.xml"),
            _reference(res_type="string", res_name="other", file="res/layout/c.xml"),
            _reference(res_type="color", res_name="ink", file="res/values/styles.xml"),
        ],
    )

    hits = store.list_resource_references(project.id, res_type="string", res_name="app_name")

    assert sorted(row.file for row in hits) == ["res/layout/a.xml", "res/layout/b.xml"]


def test_resaving_replaces_the_references_rather_than_accumulating(
    store: Store, tmp_path: Path
) -> None:
    """A re-analysis replaces the table; it does not grow a second copy of
    every edge."""
    project = Project.create(
        ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=tmp_path / "demo.apk")
    )
    store.save_project(project, tmp_path / "workspace", manifest=None)
    one = _reference()
    store.save_symbols(project.id, [], [], [], [], [], [], resource_references=[one])
    store.save_symbols(project.id, [], [], [], [], [], [], resource_references=[one])

    assert len(store.list_resource_references(project.id)) == 1


def test_a_new_analysis_clears_the_references_of_a_dropped_project(
    store: Store, tmp_path: Path
) -> None:
    """Deleting the project deletes its reference edges with it — the table
    is one of the project's own tables, not a shared one."""
    project = Project.create(
        ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=tmp_path / "demo.apk")
    )
    store.save_project(project, tmp_path / "workspace", manifest=None)
    store.save_symbols(project.id, [], [], [], [], [], [], resource_references=[_reference()])
    store.delete_project(project.id)

    assert store.list_resource_references(project.id) == []


# -- the retrieval transports ------------------------------------------------


def _project_with_references(store: Store, tmp_path: Path) -> str:
    project = Project.create(
        ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=tmp_path / "demo.apk")
    )
    store.save_project(project, tmp_path / "workspace", manifest=None)
    store.save_symbols(project.id, [], [], [], [], [], [], resource_references=[_reference()])
    return project.id


def test_the_api_answers_who_references_a_resource(tmp_path: Path) -> None:
    """The HTTP transport answers the same question the store does, and each
    row carries the locator that lands a reader on the referencing element."""
    settings = Settings(workspace=tmp_path / "workspace")
    settings.ensure_workspace()
    get_settings.cache_clear()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        store = Store.open(settings.database_path)
        project_id = _project_with_references(store, tmp_path)

        with TestClient(app) as client:
            response = client.get(f"/projects/{project_id}/resource-references")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        row = body["references"][0]
        assert row["res_type"] == "string"
        assert row["res_name"] == "app_name"
        assert row["file"] == "res/layout/activity_main.xml"
        assert row["provenance"][0]["locator"] == (
            "apktool:res/layout/activity_main.xml#line=5;TextView"
        )
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_the_api_filters_by_the_referenced_resource(tmp_path: Path) -> None:
    settings = Settings(workspace=tmp_path / "workspace")
    settings.ensure_workspace()
    get_settings.cache_clear()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        store = Store.open(settings.database_path)
        project_id = _project_with_references(store, tmp_path)

        with TestClient(app) as client:
            hit = client.get(
                f"/projects/{project_id}/resource-references",
                params={"res_type": "string", "res_name": "app_name"},
            )
            miss = client.get(
                f"/projects/{project_id}/resource-references",
                params={"res_type": "string", "res_name": "no_such_resource"},
            )

        assert hit.json()["total"] == 1
        assert miss.json()["total"] == 0
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_the_api_says_when_a_project_is_unknown(tmp_path: Path) -> None:
    settings = Settings(workspace=tmp_path / "workspace")
    settings.ensure_workspace()
    get_settings.cache_clear()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            response = client.get("/projects/apk_nope/resource-references")

        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_the_cli_lists_the_references_of_one_resource(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``dexatlas resrefs`` answers "who references this resource?" from the
    command line, with the file and line to open."""
    from typer.testing import CliRunner

    from dexatlas.cli.main import app as cli

    ws = tmp_path / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(ws))
    monkeypatch.setenv("COLUMNS", "200")
    # Settings is lru_cached; without clearing it the CLI builds a *new*
    # Settings from the environment but a stale cache would keep pointing at
    # another workspace.
    get_settings.cache_clear()
    store = Store.open(ws / "dexatlas.db")
    project_id = _project_with_references(store, tmp_path)

    result = CliRunner().invoke(cli, ["resrefs", project_id])

    assert result.exit_code == 0, result.output
    assert "@string/app_name" in result.output
    assert "res/layout/activity_main.xml" in result.output
    get_settings.cache_clear()


def test_the_cli_filters_by_resource_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    from dexatlas.cli.main import app as cli

    ws = tmp_path / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(ws))
    monkeypatch.setenv("COLUMNS", "200")
    get_settings.cache_clear()
    store = Store.open(ws / "dexatlas.db")
    project_id = _project_with_references(store, tmp_path)

    hit = CliRunner().invoke(cli, ["resrefs", project_id, "--name", "app_name"])
    miss = CliRunner().invoke(cli, ["resrefs", project_id, "--name", "no_such"])

    assert hit.exit_code == 0, hit.output
    assert "@string/app_name" in hit.output
    assert miss.exit_code == 1, miss.output
    assert "No references matched" in miss.output
    get_settings.cache_clear()


def test_the_cli_says_when_a_project_is_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    from dexatlas.cli.main import app as cli

    ws = tmp_path / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(ws))
    monkeypatch.setenv("COLUMNS", "200")
    get_settings.cache_clear()

    result = CliRunner().invoke(cli, ["resrefs", "apk_nope"])

    assert result.exit_code == 2
    assert "No such project" in result.output
    get_settings.cache_clear()
