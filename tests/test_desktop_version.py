"""The desktop application and the release must say the same version.

The defect
----------
The desktop application carried its own version number, and it had drifted
away from the release:

* ``src/dexatlas/__init__.py`` said ``1.2.0`` (the release),
* ``desktop/package.json``, ``desktop/src-tauri/tauri.conf.json`` and
  ``desktop/src-tauri/Cargo.toml`` said ``0.1.0``,
* and the MSI's ``ProductVersion`` — which comes from ``tauri.conf.json`` —
  said ``0.1.0`` too, so a version bump could never be exercised as an
  upgrade.

The settings page made it worse: it showed the *backend's* version under the
plain label "version", so the number a reader saw was not the version of the
application they had installed.

What is checked
---------------
Four files have to carry the release's number, and the page has to say which
number is whose:

* ``desktop/package.json``,
* ``desktop/src-tauri/tauri.conf.json`` (also the MSI's ``ProductVersion``),
* ``desktop/src-tauri/Cargo.toml`` (the .exe's version resource),
* ``desktop/src-tauri/Cargo.lock``.

``scripts/sync-desktop-version.py`` writes all four from
``src/dexatlas/__init__.py``; this file is the gate that notices when
somebody edits one of them by hand.

The question of whether the desktop application should carry the release's
number at all is a decision for the project owner; what is asserted here is
the state that decision was taken in, so that a later change to it is a
deliberate edit of this file rather than a silent drift.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_INIT = ROOT / "src" / "dexatlas" / "__init__.py"
PACKAGE_JSON = ROOT / "desktop" / "package.json"
TAURI_CONF = ROOT / "desktop" / "src-tauri" / "tauri.conf.json"
CARGO_TOML = ROOT / "desktop" / "src-tauri" / "Cargo.toml"
CARGO_LOCK = ROOT / "desktop" / "src-tauri" / "Cargo.lock"
WIX_TEMPLATE = ROOT / "desktop" / "src-tauri" / "wix" / "main.wxs"
SETTINGS_PAGE = ROOT / "desktop" / "src" / "pages" / "SettingsPage.tsx"
SETTINGS_VERSION = ROOT / "desktop" / "src" / "pages" / "settingsVersion.ts"

VERSION_RE = re.compile(r'^__version__\s*=\s*"([^"]+)"', re.MULTILINE)


def _release_version() -> str:
    match = VERSION_RE.search(CORE_INIT.read_text(encoding="utf-8"))
    assert match is not None, f"{CORE_INIT} 里没有 __version__"
    return match.group(1)


def _cargo_toml_version() -> str:
    match = re.search(
        r'^version = "([^"]+)"$', CARGO_TOML.read_text(encoding="utf-8"), re.MULTILINE
    )
    assert match is not None, f"{CARGO_TOML} 里没有 version"
    return match.group(1)


def _cargo_lock_version() -> str:
    match = re.search(
        r'name = "dexatlas-desktop"\nversion = "([^"]+)"',
        CARGO_LOCK.read_text(encoding="utf-8"),
    )
    assert match is not None, f"{CARGO_LOCK} 里没有 dexatlas-desktop 的条目"
    return match.group(1)


def test_every_place_carries_the_release_version() -> None:
    """The release's number, in all four places that carry it."""

    expected = _release_version()
    actual = {
        "desktop/package.json": json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))["version"],
        "desktop/src-tauri/tauri.conf.json": json.loads(TAURI_CONF.read_text(encoding="utf-8"))[
            "version"
        ],
        "desktop/src-tauri/Cargo.toml": _cargo_toml_version(),
        "desktop/src-tauri/Cargo.lock": _cargo_lock_version(),
    }
    drifted = {name: value for name, value in actual.items() if value != expected}
    assert not drifted, (
        f"发版号是 {expected}，但桌面的版本号没跟上：{drifted}；"
        "改版本号请跑 scripts/sync-desktop-version.py"
    )


def test_the_msi_version_comes_from_the_application_version() -> None:
    """The MSI's ProductVersion follows the release, it is not a second number.

    ``tauri.conf.json``'s version is what the installer takes; the template
    must not carry a number of its own, and a separate ``wix.version`` may
    only repeat the same number.
    """

    conf = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
    app_version = conf["version"]

    wix_version = conf.get("bundle", {}).get("windows", {}).get("wix", {}).get("version")
    if wix_version is not None:
        assert wix_version == app_version, (
            f"MSI 的版本（{wix_version}）与应用版本（{app_version}）不一致，"
            "安装包会报出一个与应用对不上的版本"
        )

    template = WIX_TEMPLATE.read_text(encoding="utf-8")
    product_version = re.search(r'Version="([^"]*)"', template)
    assert product_version is not None, "模板里找不到 Product 的 Version"
    assert product_version.group(1) == "{{version}}", (
        f"模板里的 Product Version 写死了 {product_version.group(1)}，"
        "它应当取应用版本（{{version}}）"
    )


def test_the_settings_page_says_whose_version_each_number_is() -> None:
    """Two numbers, two labels: the application's and the backend's."""

    rows = SETTINGS_VERSION.read_text(encoding="utf-8")
    assert '"应用版本"' in rows, "版本行里没有「应用版本」"
    assert '"后端版本（分析核心）"' in rows, "版本行里没有「后端版本」"

    page = SETTINGS_PAGE.read_text(encoding="utf-8")
    assert "versionEntries" in page, "设置页没有用 versionEntries 组装版本行"
    assert "<dt>版本</dt>" not in page, (
        "设置页还有一条光秃秃的「版本」行——读者会把它当成这个应用的版本"
    )
