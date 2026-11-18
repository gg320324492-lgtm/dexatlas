"""The image has to carry the repository's own samples, and the job has to use them.

Three claims, all checked without running Docker.

* The samples are copied into the image **after** the dependencies are
  installed. A sample copied before the last ``uv sync`` would invalidate the
  dependency layer every time a sample changed, and the layers above it --
  the backend downloads -- take minutes.
* The CI job analyses the sample by a **relative** path and checks the
  counts the run produced. The relative path is the point: it is resolved
  inside the container, where the samples sit next to the code, so it does
  not depend on how the host rewrites an argument that looks like a Windows
  path.
* The build context is what it should be. The image reads six things out of
  the repository, and the ignore list has to leave all six alone.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
DOCKERFILE = REPO_ROOT / "Dockerfile"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"


def _glob(pattern: str) -> re.Pattern[str]:
    """A glob over a path, where ``*`` does not cross a directory separator.

    Docker matches its ignore list with Go's ``filepath.Match``, where ``*``
    stops at a separator. Python's ``fnmatch`` does not, and the difference
    is the difference between excluding the root's ``docs`` and excluding
    every directory named ``docs`` in the tree.
    """
    out: list[str] = []
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            if pattern[index : index + 3] == "**/":
                out.append("(?:.*/)?")
                index += 3
                continue
            if pattern[index : index + 2] == "**":
                out.append(".*")
                index += 2
                continue
            out.append("[^/]*")
        elif char == "?":
            out.append("[^/]")
        elif char == "[":
            end = pattern.find("]", index)
            if end < 0:
                out.append(re.escape(char))
            else:
                out.append(pattern[index : end + 1])
                index = end + 1
                continue
        else:
            out.append(re.escape(char))
        index += 1
    return re.compile("".join(out))


def _excluded(relative: str, patterns: list[str]) -> bool:
    """Whether Docker's ignore list would take a path out of the build context.

    The subset of Docker's pattern language this repository's list uses. A
    pattern without a slash is matched against every path component, at any
    depth -- ``*.apk`` takes ``examples/demo-app/demo.apk`` with it, which
    is the whole reason the list has to be written with that in mind. A
    pattern with a slash is matched against the path relative to the
    context root, and against every directory above it.
    """
    parts = relative.split("/")
    candidates = [relative]
    candidates.extend("/".join(parts[:index]) for index in range(len(parts) - 1, 0, -1))
    for raw in patterns:
        pattern = raw.strip()
        if not pattern or pattern.startswith("#"):
            continue
        regex = _glob(pattern if "/" in pattern else f"**/{pattern}")
        if any(regex.fullmatch(candidate) for candidate in candidates):
            return True
    return False


def _patterns() -> list[str]:
    """The rules of the ignore list."""
    if not DOCKERIGNORE.is_file():
        return []
    return DOCKERIGNORE.read_text(encoding="utf-8").splitlines()


def _copy_sources() -> list[str]:
    """The paths the Dockerfile copies into the image."""
    sources: list[str] = []
    for line in DOCKERFILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("COPY ") or stripped.startswith("COPY --from="):
            continue
        parts = stripped.split()[1:]
        for source in parts[:-1]:
            sources.append(source.rstrip("/"))
    return sources


def _heredoc(steps: str) -> str:
    """The Python the job runs through a heredoc."""
    marker = "python3 - <<'PY'\n"
    start = steps.find(marker)
    if start < 0:
        return ""
    body = steps[start + len(marker) :]
    end = body.find("\nPY")
    return body[:end] if end >= 0 else body


def _keys_of(tree: ast.AST, name: str) -> set[str] | None:
    """The keys of the dictionary the script assigns to a name."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        return {key.value for key in node.value.keys if isinstance(key, ast.Constant)}
    return None


def test_the_samples_are_copied_after_the_dependencies_are_installed() -> None:
    """A sample copied before the last ``uv sync`` invalidates the dependency layer.

    The layers above it download JADX and Apktool, and they take minutes.
    They have to stay valid while a sample changes, so the samples go last.
    """
    lines = DOCKERFILE.read_text(encoding="utf-8").splitlines()

    syncs = [number for number, line in enumerate(lines) if "uv sync" in line]
    copies = [
        number for number, line in enumerate(lines) if line.strip() == "COPY examples/ examples/"
    ]

    assert syncs, "the Dockerfile installs no dependencies"
    assert copies, "the Dockerfile copies no sample into the image"

    last_sync = max(syncs)
    copy = copies[0]
    assert copy > last_sync, (
        "the samples are copied before the last `uv sync` (copy on line "
        f"{copy + 1}, last sync on line {last_sync + 1}), so editing a sample "
        "invalidates the dependency layer"
    )


def test_the_docker_job_analyses_the_bundled_sample_by_a_relative_path() -> None:
    """The sample is addressed by a path the container can resolve.

    An absolute path would be a path on the host, and the host rewrites an
    argument that looks like a Windows path. The samples sit next to the
    code inside the image, and the path that finds them is relative.
    """
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = "\n".join(str(step.get("run", "")) for step in workflow["jobs"]["docker"]["steps"])

    addressed = re.findall(r"dexatlas analyze (\S+)", steps)
    assert addressed, "the docker job analyses no sample"
    for path in addressed:
        assert path.startswith("examples/"), (
            f"the sample is addressed by {path!r}; the path has to be relative, "
            "so that it is resolved inside the container and not on the host"
        )


def test_the_docker_job_checks_the_counts_the_run_produced() -> None:
    """A run that found nothing has to fail the job.

    The image is checked by analysing a sample and reading the report it
    wrote. Without the counts, the job would pass on an image that analysed
    nothing at all.
    """
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = "\n".join(str(step.get("run", "")) for step in workflow["jobs"]["docker"]["steps"])

    script = _heredoc(steps)
    assert script, "the docker job reads no report"

    tree = ast.parse(script)
    floors = _keys_of(tree, "floors")
    assert floors is not None, "the job checks no floors against the counts"
    assert {"classes", "methods", "call_sites"} <= floors
    assert any(isinstance(node, ast.Assert) for node in ast.walk(tree)), (
        "the job asserts nothing about the counts it read"
    )


def _tracked_files() -> list[str]:
    """The files of the repository, as the checkout has them."""
    done = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return done.stdout.splitlines()


def test_the_ignore_list_keeps_everything_the_image_copies() -> None:
    """Nothing the Dockerfile copies may be taken out of the build context.

    The Dockerfile copies directories, so it is the files inside them that
    have to survive: a "*.apk" rule would look harmless and would take
    ``examples/demo-app/demo.apk`` with it, and the image would be left
    without the file the CI job analyses.
    """
    patterns = _patterns()
    assert patterns, "there is no ignore list, so the context carries the .git"

    sources = _copy_sources()
    assert sources, "the Dockerfile copies nothing"

    tracked = _tracked_files()
    for source in sources:
        if not Path(source).is_dir():
            assert not _excluded(source, patterns), f"{source} would not reach the image"
            continue
        inside = [name for name in tracked if name.startswith(f"{source}/")]
        assert inside, f"{source} is copied into the image and holds no file"
        for name in inside:
            assert not _excluded(name, patterns), f"{name} would not reach the image"

    for excluded in (
        ".git/config",
        ".scratch/tmp/measurement.json",
        ".venv/lib/python3.12/site-packages",
        "src/dexatlas/__pycache__/pipeline.cpython-312.pyc",
        "src/dexatlas/pipeline.pyc",
        ".pytest_cache/v/cache/lastfailed",
        ".mypy_cache/3.12/dexatlas/core/pipeline.data",
    ):
        assert _excluded(excluded, patterns), f"{excluded} would still reach the daemon"
