"""Smali path resolution.

Covers the layouts Apktool actually produces when it decodes an APK, and the attack
surface of turning a caller-supplied class name into a filesystem path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.tools.apktool.adapter import ApktoolBackend


@pytest.fixture
def apktool(settings) -> ApktoolBackend:
    return ApktoolBackend(settings)


def _smali_file(output_dir: Path, root: str, class_name: str) -> Path:
    """Write a placeholder .smali where Apktool would put it, and return the path."""
    relative = Path(*class_name.split(".")).with_suffix(".smali")
    path = output_dir / root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f".class public L{class_name.replace('.', '/')};\n", encoding="utf-8")
    return path


# -- layouts Apktool produces -----------------------------------------------


def test_finds_a_class_in_the_single_dex_layout(apktool: ApktoolBackend, tmp_path: Path) -> None:
    """`classes.dex` decodes into `smali/`."""
    expected = _smali_file(tmp_path, "smali", "com.foobar.foo.Foobar")

    assert apktool.smali_path("com.foobar.foo.Foobar", tmp_path) == expected


def test_finds_a_class_in_the_second_dex_directory(apktool: ApktoolBackend, tmp_path: Path) -> None:
    """`classes2.dex` decodes into `smali_classes2/`, a *sibling* of `smali/`.

    Apktool names these after the dex file, so the second dex is `smali_classes2`,
    the third `smali_classes3`, and so on — all under the output directory, not
    nested inside `smali/`.
    """
    _smali_file(tmp_path, "smali", "com.foobar.foo.Foobar")
    expected = _smali_file(tmp_path, "smali_classes2", "com.blafoo.bar.Blafoo")

    assert apktool.smali_path("com.blafoo.bar.Blafoo", tmp_path) == expected


def test_finds_a_class_in_the_third_dex_directory(apktool: ApktoolBackend, tmp_path: Path) -> None:
    expected = _smali_file(tmp_path, "smali_classes3", "com.third.Only")

    assert apktool.smali_path("com.third.Only", tmp_path) == expected


def test_resolves_duplicate_names_deterministically(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    """Two dexes can hold the same fully-qualified name; resolve in a fixed order."""
    first = _smali_file(tmp_path, "smali", "com.dup.Same")
    _smali_file(tmp_path, "smali_classes2", "com.dup.Same")

    assert apktool.smali_path("com.dup.Same", tmp_path) == first


def test_missing_class_returns_none(apktool: ApktoolBackend, tmp_path: Path) -> None:
    _smali_file(tmp_path, "smali", "com.foobar.foo.Foobar")

    assert apktool.smali_path("com.nope.Missing", tmp_path) is None


def test_no_smali_directory_returns_none(apktool: ApktoolBackend, tmp_path: Path) -> None:
    (tmp_path / "res").mkdir()

    assert apktool.smali_path("com.foobar.foo.Foobar", tmp_path) is None


def test_an_output_directory_that_does_not_exist_returns_none(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    """Apktool never ran, so there is nothing to look in — not a reason to raise."""
    missing = tmp_path / "never-decoded"

    assert apktool.smali_path("com.foobar.foo.Foobar", missing) is None


@pytest.mark.parametrize(
    "malformed",
    [
        "",
        ".",
        "..",
        "com.foo..Bar",  # empty segment between two separators
        "com..foo.Bar",
        "com.foo.",  # trailing separator
        ".com.foo.Bar",  # leading separator
    ],
)
def test_a_name_with_an_empty_or_dot_segment_is_not_a_class_name(
    apktool: ApktoolBackend, tmp_path: Path, malformed: str
) -> None:
    """An empty or dot-only segment is not a path component.

    ``com..foo.Bar`` splits into ``['com', '', 'foo', 'Bar']``; joining that yields
    ``com/foo/Bar`` and silently reads the wrong class, so it must be rejected outright.
    """
    _smali_file(tmp_path, "smali", "com.foobar.foo.Foobar")

    assert apktool.smali_path(malformed, tmp_path) is None


def test_empty_segments_are_rejected_before_the_component_check() -> None:
    """``_is_single_component`` never sees an empty or dot-only segment.

    It does not test for them itself — that guard lives in
    ``_class_to_relative_path``. If this contract ever breaks, a segment like ``..``
    reaches the path join and the traversal protection is gone, so the assumption is
    pinned here rather than left implicit in a comment.
    """
    from dexatlas.tools.apktool import adapter

    seen: list[str] = []
    original = adapter._is_single_component

    def spy(part: str) -> bool:
        seen.append(part)
        return original(part)

    adapter._is_single_component = spy
    try:
        # A valid name is included so the spy is provably wired up; without it an
        # empty `seen` would pass the assertion below for the wrong reason.
        for name in ("com.foo.Bar", "", ".", "..", "com..foo.Bar", "com.foo.", ".com.foo", "a...b"):
            adapter._class_to_relative_path(name)
    finally:
        adapter._is_single_component = original

    assert seen, "the spy was never called; the contract is not being exercised"
    assert all(part and part not in {".", ".."} for part in seen), (
        f"an empty or dot-only segment reached the component check: {seen!r}"
    )


def test_read_smali_returns_the_class_text(apktool: ApktoolBackend, tmp_path: Path) -> None:
    _smali_file(tmp_path, "smali_classes2", "com.blafoo.bar.Blafoo")

    text = apktool.read_smali("com.blafoo.bar.Blafoo", tmp_path)

    assert text is not None
    assert "Lcom/blafoo/bar/Blafoo;" in text


def test_read_smali_of_missing_class_returns_none(apktool: ApktoolBackend, tmp_path: Path) -> None:
    _smali_file(tmp_path, "smali", "com.foobar.foo.Foobar")

    assert apktool.read_smali("com.nope.Missing", tmp_path) is None


# -- path traversal ---------------------------------------------------------


@pytest.mark.parametrize(
    "hostile",
    [
        "../../../../etc/passwd",
        "..\\..\\..\\windows\\win.ini",
        "com.foo." + chr(0) + "Bar",
        "....//....//etc/passwd",
        "/etc/passwd",
        "com.foo/../../secret",
        "com..foo.Bar",
        "com.foo..%2f..%2fetc%2fpasswd",
    ],
)
def test_class_name_cannot_escape_the_smali_directories(
    apktool: ApktoolBackend, tmp_path: Path, hostile: str
) -> None:
    """A class name arrives from an analysed APK, so it is untrusted input.

    Splitting on "." and joining the parts turns `../../etc/passwd` into a path that
    walks straight out of the decoded output. Resolution must either stay inside the
    smali directories or return None — never read an arbitrary file.
    """
    _smali_file(tmp_path, "smali", "com.foobar.foo.Foobar")

    found = apktool.smali_path(hostile, tmp_path)

    if found is None:
        return
    resolved = found.resolve()
    assert resolved.is_relative_to(tmp_path.resolve()), (
        f"{hostile!r} resolved outside the output directory: {resolved}"
    )
    assert "passwd" not in str(resolved).lower()


def test_absolute_path_as_class_name_cannot_read_an_absolute_path(
    apktool: ApktoolBackend, tmp_path: Path
) -> None:
    """A name that is already a filesystem path must not be honoured as one."""
    secret = tmp_path / "outside.secret"
    secret.write_text("should never be read", encoding="utf-8")
    _smali_file(tmp_path, "smali", "com.foobar.foo.Foobar")

    assert apktool.smali_path(str(secret), tmp_path) is None
    assert apktool.read_smali(str(secret), tmp_path) is None
