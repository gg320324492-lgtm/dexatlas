#!/usr/bin/env bash
# Run the suite on real Linux, in WSL.
#
# The Windows machine is where the code is written, and it is not where CI
# runs. Two defects in a row passed every local test and failed on the Linux
# runner -- a temporary file's .file attribute, and a path component longer
# than a file name may hold. This script closes that gap: it copies the tree
# into WSL and runs the suite there.
#
# The source is given as an argument, and it is copied as an archive of a
# commit when one is named -- not as the working tree, which the agents are
# editing while this runs. Copying a working tree measures whatever was on
# disk at that moment, which is not a thing anybody can reproduce.
#
#   linux-check.sh                       # the working tree at the repository
#   linux-check.sh --commit HEAD lint    # an archive of that commit
#   linux-check.sh --dir /some/path tests
#
# It has to be run from inside WSL: the tree it copies has to be a Linux
# path, and the virtualenv it builds has to be a Linux one.

set -uo pipefail

REPO_DEFAULT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${DEXATLAS_LINUX_DEST:-$HOME/dexatlas-linux}"

MODE="tree"
SRC="$REPO_DEFAULT"
TASK="tests"

while [ $# -gt 0 ]; do
    case "$1" in
        --commit) MODE="commit"; SRC="$2"; shift 2 ;;
        --dir)    MODE="dir";    SRC="$2"; shift 2 ;;
        -*)       echo "unknown option: $1" >&2; exit 2 ;;
        *)        TASK="$1"; shift ;;
    esac
done

mkdir -p "$DEST" || exit 1

# The destination is reused, so the tar lands on top of the previous run's
# tree -- and a file that is in the previous run but not in this one stays
# there and breaks the collection of this run. Two parallel chips hit exactly
# that: one branch's leftover test file failed the other branch's run, at
# collection, before a single test ran.
#
# The virtualenv is kept: it is what makes `uv run --no-sync` work here, and
# rebuilding it for every run is slow. Everything else is cleared.
if [ -d "$DEST" ]; then
  find "$DEST" -mindepth 1 -maxdepth 1 ! -name '.venv' -exec rm -rf {} +
fi

case "$MODE" in
    commit)
        # A commit: export exactly that tree, so the run is reproducible.
        git -C "$REPO_DEFAULT" archive --format=tar "$SRC" | (cd "$DEST" && tar -xf -) || exit 1
        ;;
    dir)
        (cd "$SRC" && tar -cf - --exclude=.venv --exclude=build --exclude=__pycache__ \
            --exclude=.pytest_cache --exclude=.mypy_cache --exclude=.git \
            --exclude=.claude --exclude=.scratch .) \
            | (cd "$DEST" && tar -xf -) || exit 1
        ;;
    tree)
        (cd "$SRC" && tar -cf - --exclude=.venv --exclude=build --exclude=__pycache__ \
            --exclude=.pytest_cache --exclude=.mypy_cache --exclude=.git \
            --exclude=.claude --exclude=.scratch .) \
            | (cd "$DEST" && tar -xf -) || exit 1
        ;;
esac

cd "$DEST" || exit 1
export PATH="$HOME/.local/bin:$PATH"

# The virtualenv is kept between runs, so it can be out of step with the tree
# it is supposed to be measuring: an extra added to pyproject.toml does not
# reach a venv that was built before it. The sync is quick when nothing has
# changed, and it is the difference between a check of this tree and a check
# of the tree the venv was built from.
uv sync --extra dev --extra analysis --extra mcp --frozen || exit 1

case "$TASK" in
    tests) uv run --no-sync pytest -q ;;
    lint)  uv run --no-sync ruff check . && uv run --no-sync ruff format --check . && uv run --no-sync mypy ;;
    *)     uv run --no-sync pytest -q "$TASK" ;;
esac
