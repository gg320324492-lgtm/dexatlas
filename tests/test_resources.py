"""The resource table, read out of Apktool's decoded ``res/`` tree.

The gap this file closes was visible in one query: the demo app's resource
string ``DexAtlas Demo`` was in no index at all, so a hard-coded key that
lived in ``strings.xml`` was invisible to ``dexatlas search``.

The parsing tests write their own ``res/`` tree, so they do not depend on
which backends the machine happens to have. The end-to-end test runs against
the real demo APK and skips itself when Apktool is not installed.
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
    ProjectStatus,
    Provenance,
    ResourceKind,
    ResourceString,
)
from dexatlas.core.pipeline import Analyzer
from dexatlas.core.storage import Store
from dexatlas.tools.apktool.adapter import MAX_RESOURCE_ERRORS, ApktoolBackend

#: A SHA-256 that is obviously a placeholder but has the right shape.
FAKE_SHA256 = "a" * 64

#: The resource table of the demo application, as Apktool decodes it.
DEMO_RESOURCE_VALUE = "DexAtlas Demo"

DEMO_APK = Path(__file__).parent.parent / "examples" / "demo-app" / "demo.apk"

STRINGS_XML = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">DexAtlas Demo</string>
    <string name="greeting">Hello, %s</string>
</resources>
"""


def _values_file(output_dir: Path, relative: str, body: str) -> Path:
    """Write one file into the decoded resource tree."""
    path = output_dir / "res" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


# -- reading the tree --------------------------------------------------------


def test_a_string_is_read_from_the_values_directory(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    _values_file(tmp_path, "values/strings.xml", STRINGS_XML)

    rows, errors = apktool.read_resources(tmp_path, FAKE_SHA256)

    assert errors == []
    assert [(row.name, row.value) for row in rows] == [
        ("app_name", "DexAtlas Demo"),
        ("greeting", "Hello, %s"),
    ]


def test_the_locator_points_into_the_apktool_output_tree(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    """The locator names a place inside the decoded tree, never a path on the
    machine that ran the analysis."""
    _values_file(tmp_path, "values/strings.xml", STRINGS_XML)

    rows, _ = apktool.read_resources(tmp_path, FAKE_SHA256)

    assert rows[0].provenance[0].locator == "apktool:res/values/strings.xml"
    assert rows[0].provenance[0].tool == "apktool"
    assert rows[0].provenance[0].apk_sha256 == FAKE_SHA256
    assert rows[0].file == "res/values/strings.xml"


def test_a_qualified_values_directory_keeps_its_qualifier(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    """The same name in two languages is two resources, and each points at its
    own file."""
    _values_file(tmp_path, "values/strings.xml", STRINGS_XML)
    _values_file(
        tmp_path,
        "values-zh/strings.xml",
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<resources><string name="app_name">DexAtlas 演示</string></resources>',
    )

    rows, errors = apktool.read_resources(tmp_path, FAKE_SHA256)

    assert errors == []
    qualified = {(row.name, row.qualifier): row for row in rows}
    assert set(qualified) == {("app_name", None), ("greeting", None), ("app_name", "zh")}
    assert qualified[("app_name", None)].value == "DexAtlas Demo"
    assert qualified[("app_name", "zh")].value == "DexAtlas 演示"
    assert qualified[("app_name", "zh")].file == "res/values-zh/strings.xml"
    assert qualified[("app_name", "zh")].provenance[0].locator == (
        "apktool:res/values-zh/strings.xml"
    )
    # The qualified name says which one it is, so a listing can show both.
    assert qualified[("app_name", None)].qualified_name == "app_name"
    assert qualified[("app_name", "zh")].qualified_name == "app_name (zh)"


def test_a_string_array_yields_one_row_per_item(apktool: ApktoolBackend, tmp_path: Path) -> None:
    _values_file(
        tmp_path,
        "values/arrays.xml",
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<resources>\n"
        '  <string-array name="endpoints">\n'
        "    <item>https://api.example.com/v1</item>\n"
        "    <item>https://api.example.com/v2</item>\n"
        "  </string-array>\n"
        "</resources>",
    )

    rows, errors = apktool.read_resources(tmp_path, FAKE_SHA256)

    assert errors == []
    assert [(row.value, row.kind) for row in rows] == [
        ("https://api.example.com/v1", ResourceKind.STRING_ARRAY),
        ("https://api.example.com/v2", ResourceKind.STRING_ARRAY),
    ]
    assert all(row.name == "endpoints" for row in rows)


def test_a_plural_yields_one_row_per_quantity(apktool: ApktoolBackend, tmp_path: Path) -> None:
    _values_file(
        tmp_path,
        "values/plurals.xml",
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<resources>\n"
        '  <plurals name="songs">\n'
        '    <item quantity="one">%d song</item>\n'
        '    <item quantity="other">%d songs</item>\n'
        "  </plurals>\n"
        "</resources>",
    )

    rows, errors = apktool.read_resources(tmp_path, FAKE_SHA256)

    assert errors == []
    assert [(row.quantity, row.value) for row in rows] == [
        ("one", "%d song"),
        ("other", "%d songs"),
    ]
    assert all(row.kind is ResourceKind.PLURAL for row in rows)


def test_a_value_that_is_not_text_is_not_a_string(apktool: ApktoolBackend, tmp_path: Path) -> None:
    """Colours, dimensions and the rest describe how the app looks.

    A "string index" full of them would answer no question a reader asked, so
    they are not indexed. The decision is pinned here so that widening it later
    is a deliberate act.
    """
    _values_file(
        tmp_path,
        "values/colors.xml",
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<resources>\n"
        '  <color name="brand">#FF00FF</color>\n'
        '  <dimen name="pad">16dp</dimen>\n'
        '  <bool name="dark">false</bool>\n'
        "</resources>",
    )

    rows, errors = apktool.read_resources(tmp_path, FAKE_SHA256)

    assert errors == []
    assert rows == []


def test_a_file_that_will_not_parse_is_an_error_and_the_others_are_still_read(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    """One broken file must not cost the whole resource table."""
    _values_file(tmp_path, "values/strings.xml", STRINGS_XML)
    _values_file(tmp_path, "values/broken.xml", "<resources><string name='x'>")

    rows, errors = apktool.read_resources(tmp_path, FAKE_SHA256)

    assert len(errors) == 1
    assert errors[0].code.value == "parse_error"
    assert "res/values/broken.xml" in errors[0].message
    assert [row.name for row in rows] == ["app_name", "greeting"]


def test_an_entity_declaration_is_refused(apktool: ApktoolBackend, tmp_path: Path) -> None:
    """The resource table comes out of an untrusted APK.

    An entity declaration is how a plain XML parser is made to expand a
    bomb, so the parser refuses it — the file is an error, not a hang.
    """
    _values_file(
        tmp_path,
        "values/evil.xml",
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<!DOCTYPE resources [\n"
        '  <!ENTITY boom "aaaaaaaaaa">\n'
        "]>\n"
        '<resources><string name="x">&boom;</string></resources>',
    )

    rows, errors = apktool.read_resources(tmp_path, FAKE_SHA256)

    assert rows == []
    assert len(errors) == 1
    assert errors[0].code.value == "parse_error"


def test_an_apk_without_a_resource_tree_reads_nothing(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    rows, errors = apktool.read_resources(tmp_path, FAKE_SHA256)

    assert rows == []
    assert errors == []


def test_an_empty_values_file_is_an_error(apktool: ApktoolBackend, tmp_path: Path) -> None:
    """A file with no root element cannot be read, and saying so is better than
    reading nothing and looking like an empty resource table."""
    _values_file(tmp_path, "values/empty.xml", "")

    rows, errors = apktool.read_resources(tmp_path, FAKE_SHA256)

    assert rows == []
    assert len(errors) == 1
    assert errors[0].code.value == "parse_error"
    assert "res/values/empty.xml" in errors[0].message


def test_a_child_that_is_not_an_item_is_ignored(apktool: ApktoolBackend, tmp_path: Path) -> None:
    """A ``<string-array>`` may hold other elements; only ``<item>`` is text."""
    _values_file(
        tmp_path,
        "values/arrays.xml",
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<resources>\n"
        '  <string-array name="endpoints">\n'
        "    <item>https://api.example.com/v1</item>\n"
        "    <note>ignored</note>\n"
        "  </string-array>\n"
        "</resources>",
    )

    rows, errors = apktool.read_resources(tmp_path, FAKE_SHA256)

    assert errors == []
    assert [row.value for row in rows] == ["https://api.example.com/v1"]


def test_too_many_broken_files_are_summarised(apktool: ApktoolBackend, tmp_path: Path) -> None:
    """A hostile APK must not be able to fill the report with thousands of
    near-identical rows: the errors are capped, and the cap says how many were
    left out."""
    for index in range(MAX_RESOURCE_ERRORS + 4):
        _values_file(tmp_path, f"values/broken{index}.xml", "<resources><string name='x'>")

    rows, errors = apktool.read_resources(tmp_path, FAKE_SHA256)

    assert rows == []
    assert len(errors) == MAX_RESOURCE_ERRORS + 1
    assert "further resource file(s) could not be parsed" in errors[-1].message


# -- storage -----------------------------------------------------------------


def _resource(name: str = "app_name", value: str = "DexAtlas Demo") -> ResourceString:
    return ResourceString(
        name=name,
        value=value,
        kind=ResourceKind.STRING,
        file="res/values/strings.xml",
        provenance=[
            Provenance(
                tool="apktool",
                tool_version="2.11.1",
                apk_sha256=FAKE_SHA256,
                locator="apktool:res/values/strings.xml",
            )
        ],
    )


def test_a_read_array_survives_the_database(
    apktool: ApktoolBackend, store: Store, tmp_path: Path
) -> None:
    """The whole path: read out of the tree, then written to the database.

    Both items of the array have to arrive. A row that is overwritten on the
    way in is a declaration that the index never held.
    """
    _values_file(
        tmp_path,
        "values/arrays.xml",
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<resources>\n"
        '  <string-array name="endpoints">\n'
        "    <item>https://api.example.com/v1</item>\n"
        "    <item>https://api.example.com/v2</item>\n"
        "  </string-array>\n"
        "</resources>",
    )
    rows, errors = apktool.read_resources(tmp_path, FAKE_SHA256)
    assert errors == []

    project = Project.create(
        ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=tmp_path / "demo.apk")
    )
    store.save_project(project, tmp_path / "workspace", manifest=None)

    counts = store.save_symbols(project.id, [], [], [], [], [], rows)

    assert counts.resources == 2
    assert [row.value for row in store.list_resources(project.id)] == [
        "https://api.example.com/v1",
        "https://api.example.com/v2",
    ]


def test_the_resources_table_round_trips(store: Store, tmp_path: Path) -> None:
    project = Project.create(
        ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=tmp_path / "demo.apk")
    )
    store.save_project(project, tmp_path / "workspace", manifest=None)

    counts = store.save_symbols(project.id, [], [], [], [], [], [_resource()])

    assert counts.resources == 1
    stored = store.list_resources(project.id)
    assert len(stored) == 1
    assert stored[0].name == "app_name"
    assert stored[0].value == "DexAtlas Demo"
    assert stored[0].file == "res/values/strings.xml"
    assert stored[0].provenance[0].locator == "apktool:res/values/strings.xml"


def test_the_items_of_one_array_do_not_overwrite_each_other(store: Store, tmp_path: Path) -> None:
    """Two items of one ``<string-array>`` are two declarations.

    They share a name and a file, so the position inside the array is the only
    thing that tells them apart. Without it, the second item would take the
    first one's place and the count would be one short of what was declared.
    """
    project = Project.create(
        ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=tmp_path / "demo.apk")
    )
    store.save_project(project, tmp_path / "workspace", manifest=None)

    items = [
        ResourceString(
            name="endpoints",
            value=value,
            kind=ResourceKind.STRING_ARRAY,
            position=position,
            file="res/values/arrays.xml",
            provenance=[
                Provenance(
                    tool="apktool",
                    tool_version="2.11.1",
                    apk_sha256=FAKE_SHA256,
                    locator="apktool:res/values/arrays.xml",
                )
            ],
        )
        for position, value in enumerate(
            ["https://api.example.com/v1", "https://api.example.com/v2"]
        )
    ]

    counts = store.save_symbols(project.id, [], [], [], [], [], items)

    assert counts.resources == 2
    stored = store.list_resources(project.id)
    assert [row.value for row in stored] == [
        "https://api.example.com/v1",
        "https://api.example.com/v2",
    ]
    assert [row.position for row in stored] == [0, 1]


def test_a_resource_can_be_looked_up_by_its_name(store: Store, tmp_path: Path) -> None:
    project = Project.create(
        ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=tmp_path / "demo.apk")
    )
    store.save_project(project, tmp_path / "workspace", manifest=None)
    store.save_symbols(project.id, [], [], [], [], [], [_resource()])

    assert len(store.list_resources(project.id, name="app_name")) == 1
    assert store.list_resources(project.id, name="nothing_like_this") == []


def test_resaving_replaces_the_resources_rather_than_accumulating(
    store: Store, tmp_path: Path
) -> None:
    project = Project.create(
        ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=tmp_path / "demo.apk")
    )
    store.save_project(project, tmp_path / "workspace", manifest=None)

    store.save_symbols(project.id, [], [], [], [], [], [_resource()])
    counts = store.save_symbols(project.id, [], [], [], [], [], [])

    assert counts.resources == 0
    assert store.list_resources(project.id) == []


def test_a_resource_string_is_searchable(store: Store, tmp_path: Path) -> None:
    """The reason the resource table is read at all: a key in ``strings.xml``
    has to be findable."""
    project = Project.create(
        ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=tmp_path / "demo.apk")
    )
    store.save_project(project, tmp_path / "workspace", manifest=None)
    store.save_symbols(project.id, [], [], [], [], [], [_resource()])

    hits = store.search(project.id, "DexAtlas Demo")

    assert hits, "the resource string was not found by its value"
    assert hits[0]["kind"] == "resource"
    assert hits[0]["name"] == "app_name"


# -- the pipeline, end to end ------------------------------------------------


@pytest.fixture
def analyzer(settings: Settings) -> Analyzer:
    return Analyzer(settings)


@pytest.mark.slow
@pytest.mark.skipif(ApktoolBackend(Settings()).resolve() is None, reason="apktool not installed")
def test_the_demo_app_resource_is_indexed(analyzer: Analyzer) -> None:
    """The blind spot, closed: the demo app's resource string is findable."""
    if not DEMO_APK.is_file():
        pytest.skip("demo APK missing")

    result = analyzer.analyze(DEMO_APK)
    project = result.project

    assert project.resource_count == 1, "the demo app declares one resource string"

    rows = analyzer.store.list_resources(project.id)
    assert len(rows) == 1
    assert rows[0].name == "app_name"
    assert rows[0].value == DEMO_RESOURCE_VALUE
    assert rows[0].file == "res/values/strings.xml"
    assert rows[0].provenance[0].locator == "apktool:res/values/strings.xml"


@pytest.mark.slow
@pytest.mark.skipif(ApktoolBackend(Settings()).resolve() is None, reason="apktool not installed")
def test_the_demo_app_resource_is_searchable(analyzer: Analyzer) -> None:
    if not DEMO_APK.is_file():
        pytest.skip("demo APK missing")

    result = analyzer.analyze(DEMO_APK)

    hits = analyzer.search(result.project.id, DEMO_RESOURCE_VALUE)

    assert hits, "the resource string is not in the search index"
    assert any(hit["kind"] == "resource" for hit in hits)


@pytest.mark.slow
@pytest.mark.skipif(ApktoolBackend(Settings()).resolve() is None, reason="apktool not installed")
def test_the_report_counts_the_resources_it_indexed(analyzer: Analyzer) -> None:
    """The number in the report has to be the number of rows in the table."""
    from dexatlas.reports.json_report import build_json_report
    from dexatlas.reports.markdown import render_markdown

    if not DEMO_APK.is_file():
        pytest.skip("demo APK missing")

    result = analyzer.analyze(DEMO_APK)
    report = build_json_report(result)
    markdown = render_markdown(result)

    rows = len(analyzer.store.list_resources(result.project.id))
    assert report["project"]["resource_count"] == rows
    assert report["summary"]["resource_strings"] == rows
    assert f"| Resource strings indexed | {rows} |" in markdown


@pytest.mark.slow
@pytest.mark.skipif(ApktoolBackend(Settings()).resolve() is None, reason="apktool not installed")
def test_a_resource_string_is_not_an_evidence_record(analyzer: Analyzer) -> None:
    """String constants are not evidence, and neither are resource strings.

    Promoting them would change what the evidence table means.
    """
    if not DEMO_APK.is_file():
        pytest.skip("demo APK missing")

    result = analyzer.analyze(DEMO_APK)

    summaries = " ".join(item.summary for item in result.evidence)
    assert DEMO_RESOURCE_VALUE not in summaries
    details = " ".join(str(value) for item in result.evidence for value in item.detail.values())
    assert DEMO_RESOURCE_VALUE not in details


# -- the CLI and the API ----------------------------------------------------


@pytest.fixture
def seeded_resource_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, Path]:
    """A project with one indexed resource, seeded through the storage layer.

    The workspace is handed back with it: the API and the CLI have to read the
    same database the seed wrote, and each of them resolves its own settings.
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("DEXATLAS_WORKSPACE", str(workspace))
    monkeypatch.setenv("COLUMNS", "200")
    get_settings.cache_clear()
    try:
        store = Store.open(get_settings().database_path)
        project = Project(
            id=Project.new_id(FAKE_SHA256),
            apk=ApkMetadata(sha256=FAKE_SHA256, size_bytes=1, path=Path("demo.apk")),
            status=ProjectStatus.COMPLETED,
            resource_count=1,
        )
        store.save_project(project, workspace, manifest=None)
        store.save_symbols(project.id, [], [], [], [], [], [_resource()])
        return project.id, workspace
    finally:
        get_settings.cache_clear()


def test_the_cli_lists_the_resources(seeded_resource_project: tuple[str, Path]) -> None:
    from typer.testing import CliRunner

    from dexatlas.cli.main import app as cli

    project_id, _ = seeded_resource_project
    result = CliRunner().invoke(cli, ["resources", project_id])

    assert result.exit_code == 0
    assert "app_name" in result.stdout
    assert "DexAtlas Demo" in result.stdout
    assert "res/values/strings.xml" in result.stdout
    assert "apktool:res/values/strings.xml" in result.stdout


def test_the_cli_search_finds_a_resource_string(
    seeded_resource_project: tuple[str, Path],
) -> None:
    from typer.testing import CliRunner

    from dexatlas.cli.main import app as cli

    project_id, _ = seeded_resource_project
    result = CliRunner().invoke(cli, ["search", project_id, "DexAtlas Demo"])

    assert result.exit_code == 0
    assert "resource" in result.stdout
    assert "app_name" in result.stdout


def _client_for(workspace: Path) -> TestClient:
    """A client wired to the workspace the seed wrote into."""
    settings = Settings(workspace=workspace)
    settings.ensure_workspace()
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_the_api_lists_the_resources(seeded_resource_project: tuple[str, Path]) -> None:
    project_id, workspace = seeded_resource_project

    with _client_for(workspace) as client:
        response = client.get(f"/projects/{project_id}/resources")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["resources"][0]["name"] == "app_name"
    assert body["resources"][0]["value"] == "DexAtlas Demo"
    assert body["resources"][0]["file"] == "res/values/strings.xml"
    assert body["resources"][0]["provenance"][0]["locator"] == "apktool:res/values/strings.xml"


def test_the_api_project_carries_the_resource_count(
    seeded_resource_project: tuple[str, Path],
) -> None:
    project_id, workspace = seeded_resource_project

    with _client_for(workspace) as client:
        response = client.get(f"/projects/{project_id}")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["resource_count"] == 1
