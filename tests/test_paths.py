"""The rule that turns a class name into a path.

`class_to_relative_path` is the one place that decides whether a name that
arrives from an HTTP request or from an analysed APK may be turned into a path
at all. Both backends use it, so a rule that lived in one of them would be a
rule the other one quietly lacked — which is how the JADX backend came to read
files outside the output tree while the Apktool backend refused to.

These tests pin the rule itself. The flows that depend on it are attacked in
`test_jadx_source_paths.py` and `test_apktool_smali.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dexatlas.core.paths import (
    MAX_COMPONENT_BYTES,
    class_to_relative_path,
    display_path,
    is_inside,
    is_single_component,
)

#: The names that are not class names. Each one is refused for a different
#: reason, and the reason is the point: a rule that refuses them for one
#: reason and lets another through is a rule with a hole in it.
REFUSED = [
    ("absolute", "/etc/passwd"),
    ("windows-absolute", "C:/Windows/System32"),
    ("unc", "\\\\server\\share\\file"),
    ("drive-relative", "C:file"),
    ("separator", "com/foo/Bar"),
    ("backslash", "com\\foo\\Bar"),
    ("parent", "com..foo.Bar"),
    ("empty-segment", "com..Bar"),
    ("trailing-dot", "com.foo."),
    ("wildcard", "com.foo.*"),
    ("question", "com.foo?"),
    ("bracket", "com.foo[0]"),
    ("control", "com.foo." + chr(7) + "Bar"),
    ("nul", "com.foo." + chr(0) + "Bar"),
]


@pytest.mark.parametrize(("name_id", "name"), REFUSED, ids=[name_id for name_id, _ in REFUSED])
def test_a_name_that_is_not_a_class_name_is_refused(name_id: str, name: str) -> None:
    """A name that would change the shape of the path is refused, not normalised."""
    assert class_to_relative_path(name, ".java") is None, name_id


def test_a_class_name_becomes_a_path() -> None:
    """The ordinary case: the name is a class name and the path is under it."""
    assert class_to_relative_path("com.example.demo.Crypto", ".java") == Path(
        "com/example/demo/Crypto.java"
    )


def test_a_name_longer_than_a_file_name_may_hold_is_refused() -> None:
    """A component the filesystem cannot hold is not a file name.

    POSIX caps a component's name at 255 bytes and Windows caps it at the same
    number, so a longer component cannot name a file anywhere. The refusal has
    to happen here rather than at the filesystem: a name that long is answered
    by the operating system with an *error* rather than with "no such file",
    and the caller is not supposed to have to catch that.
    """
    too_long = "com." + "a" * (MAX_COMPONENT_BYTES + 1) + ".Bar"
    assert class_to_relative_path(too_long, ".java") is None

    # Exactly at the limit is still a name a file can have.
    at_the_limit = "com." + "a" * MAX_COMPONENT_BYTES + ".Bar"
    assert class_to_relative_path(at_the_limit, ".java") is not None


def test_the_length_is_counted_in_bytes_not_characters() -> None:
    """A component of multi-byte characters is measured the way a filesystem measures it."""
    # A character of three bytes, so a third of the limit in characters is over it.
    over = "中" * (MAX_COMPONENT_BYTES // 3 + 1)
    assert len(over) < MAX_COMPONENT_BYTES, "the name is short in characters"
    assert not is_single_component(over)

    at_the_limit = "中" * (MAX_COMPONENT_BYTES // 3)
    assert is_single_component(at_the_limit)


def test_a_single_component_is_about_being_one_component() -> None:
    """The rule is about shape, not about being a class name."""
    assert is_single_component("Crypto")
    assert not is_single_component("a/b")
    assert not is_single_component("..")
    assert not is_single_component(".")


def test_a_path_is_reported_by_its_name_only() -> None:
    """A path that names the server's filesystem says more about the server than the analysis."""
    assert display_path(Path("/home/runner/work/dexatlas/examples/demo.apk")) == "demo.apk"


def test_a_link_out_of_the_tree_is_not_inside_it(tmp_path: Path) -> None:
    """The check resolves links, so a link cannot smuggle a file in from outside."""
    root = tmp_path / "tree"
    root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")

    link = root / "link.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):  # pragma: no cover - no symlinks here
        pytest.skip("this filesystem has no symlinks")

    assert not is_inside(root, link)
    # A file that does not exist yet is still inside the tree, if its path says so.
    assert is_inside(root, root / "real.txt")
