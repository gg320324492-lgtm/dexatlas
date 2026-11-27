#!/usr/bin/env python3
"""Keep the desktop application's version number in step with the release.

    uv run --no-sync python scripts/sync-desktop-version.py           # write
    uv run --no-sync python scripts/sync-desktop-version.py --check   # verify only

Where the version of this project lives
---------------------------------------
``src/dexatlas/__init__.py`` holds ``__version__`` and it is what
``scripts/check-version-claims.py`` reads when a document claims "the newest
version is v1.2.0". It is therefore the one place the number comes from.

The desktop application used to carry its own number: ``desktop/package.json``,
``desktop/src-tauri/tauri.conf.json`` and ``desktop/src-tauri/Cargo.toml`` all
said ``0.1.0`` while the release said ``1.2.0``. Three consequences, all found
by installing the MSI on a real machine (2026-11-27):

* the settings page showed the *backend's* version under the plain label
  "version", so a reader took it for the version of the application they had
  installed;
* the MSI's ``ProductVersion`` stayed at ``0.1.0`` forever, so a version bump
  could not be exercised as an upgrade;
* nothing failed when the numbers drifted, because nothing compared them.

What this script writes
-----------------------
Four files, all of which have to agree with each other and with the release:

* ``desktop/package.json`` — the npm package;
* ``desktop/src-tauri/tauri.conf.json`` — the application version, which is
  also where the MSI's ``ProductVersion`` comes from;
* ``desktop/src-tauri/Cargo.toml`` — the crate version, which is the version
  resource of the ``.exe`` and what the Tauri shell reports as the
  application's own version;
* ``desktop/src-tauri/Cargo.lock`` — the same crate, in the lock file.

``tests/test_desktop_version.py`` asserts that they agree, so a hand edit that
changes one of them fails the suite instead of shipping.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CORE_INIT = ROOT / "src" / "dexatlas" / "__init__.py"
PACKAGE_JSON = ROOT / "desktop" / "package.json"
TAURI_CONF = ROOT / "desktop" / "src-tauri" / "tauri.conf.json"
CARGO_TOML = ROOT / "desktop" / "src-tauri" / "Cargo.toml"
CARGO_LOCK = ROOT / "desktop" / "src-tauri" / "Cargo.lock"

VERSION_RE = re.compile(r'^__version__\s*=\s*"([^"]+)"', re.MULTILINE)


def read_release_version() -> str:
    """The release version, read from the package that carries it."""
    match = VERSION_RE.search(CORE_INIT.read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit(f"在 {CORE_INIT} 里找不到 __version__")
    return match.group(1)


def _replace_in_json(path: Path, version: str) -> str:
    """Replace the top-level "version" of a JSON file, keeping its layout."""
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r'^(  "version": )"[^"]*"', re.MULTILINE)
    if not pattern.search(text):
        raise SystemExit(f"{path} 里没有顶层 version 字段")
    return pattern.sub(lambda m: f'{m.group(1)}"{version}"', text, count=1)


def _replace_in_cargo_toml(path: Path, version: str) -> str:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r'^version = "[^"]*"$', re.MULTILINE)
    if not pattern.search(text):
        raise SystemExit(f"{path} 里没有 version 字段")
    return pattern.sub(f'version = "{version}"', text, count=1)


def _replace_in_cargo_lock(path: Path, version: str) -> str:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r'(name = "dexatlas-desktop"\nversion = )"[^"]*"', re.MULTILINE)
    if not pattern.search(text):
        raise SystemExit(f"{path} 里没有 dexatlas-desktop 的条目")
    return pattern.sub(lambda m: f'{m.group(1)}"{version}"', text, count=1)


def render(version: str) -> dict[Path, str]:
    """The four files' new contents, as text."""
    return {
        PACKAGE_JSON: _replace_in_json(PACKAGE_JSON, version),
        TAURI_CONF: _replace_in_json(TAURI_CONF, version),
        CARGO_TOML: _replace_in_cargo_toml(CARGO_TOML, version),
        CARGO_LOCK: _replace_in_cargo_lock(CARGO_LOCK, version),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="只检查，不写文件；有不一致时退出码为 1",
    )
    args = parser.parse_args(argv)

    version = read_release_version()
    wanted = render(version)
    stale = [
        path for path, content in wanted.items() if path.read_text(encoding="utf-8") != content
    ]

    if args.check:
        if not stale:
            print(f"桌面应用的版本号与发版号一致：{version}")
            return 0
        print(f"桌面应用的版本号与发版号（{version}）不一致：", file=sys.stderr)
        for path in stale:
            print(f"  {path.relative_to(ROOT)}", file=sys.stderr)
        return 1

    for path, content in wanted.items():
        if path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8", newline="\n")
            print(f"已更新 {path.relative_to(ROOT)} → {version}")
    if not stale:
        print(f"桌面应用的版本号已经是 {version}，没有改动。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
