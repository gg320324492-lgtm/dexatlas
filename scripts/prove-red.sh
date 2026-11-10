#!/usr/bin/env bash
# Prove that a regression test actually fails without the fix it claims to pin.
#
#   prove-red.sh <file> <test-node-id> [<file> <test-node-id> ...]
#
# The claim is "this test fails on the previous implementation". The way to
# check that is not to take the claim's word for it: put the pre-fix version
# of the source file back, under the *new* test, and watch it go red.
#
# The tree is copied into a throwaway worktree, so the merged main checkout is
# never touched. The new tests come from the merged tree; the source file
# comes from the commit before the merge.
#
# A test that passes without the fix proves nothing -- it is the failure mode
# this project has already been bitten by, where a green suite was testing the
# path that was not broken.
#
# The base is the commit before the merge by default; pass one to choose:
#
#   prove-red.sh --base <commit> <file> <test-node-id>

set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
BASE=""
SCRATCH="${DEXATLAS_PROVE_RED_DIR:-${TMPDIR:-/tmp}/dexatlas-prove-red}"

while [ $# -gt 0 ]; do
  case "$1" in
    --base) BASE="$2"; shift 2 ;;
    -*) echo "unknown option: $1" >&2; exit 2 ;;
    *) break ;;
  esac
done

if [ $# -lt 2 ]; then
  echo "usage: prove-red.sh [--base <commit>] <file> <test-node-id> ..." >&2
  exit 2
fi

cd "$REPO" || exit 1

if [ -z "$BASE" ]; then
  BASE=$(git rev-parse HEAD~1)
fi
MERGED=$(git rev-parse HEAD)
echo "base:    $BASE"
echo "merged:  $MERGED"

rm -rf "$SCRATCH"
git worktree add --detach "$SCRATCH" "$MERGED" > /dev/null || exit 1

cd "$SCRATCH" || exit 1

# The scratch worktree needs its own environment. The main checkout's venv
# holds an editable install that points at *its* src, so reusing it would
# measure the wrong code -- the very mistake this project is trying to catch.
uv sync --extra dev --extra analysis > /dev/null 2>&1 || {
  echo "could not build the scratch environment"
  exit 1
}

status=0
while [ $# -gt 0 ]; do
  file="$1"
  test="$2"
  shift 2
  echo
  echo "### $test  (without the fix to $file) ###"
  git -C "$REPO" show "$BASE:$file" > "$file" || { echo "could not read $file at the base"; status=1; continue; }
  uv run --no-sync pytest -q -p no:cacheprovider "$test" > /tmp/prove-red.txt 2>&1
  code=$?
  tail -12 /tmp/prove-red.txt
  if [ $code -eq 0 ]; then
    echo "NOT PROVEN: $test passes without the fix to $file"
    status=1
  else
    echo "PROVEN: $test fails without the fix to $file"
  fi
  git -C "$REPO" show "$MERGED:$file" > "$file"
done

cd "$REPO" || exit 1
git worktree remove --force "$SCRATCH" > /dev/null 2>&1
git worktree prune

if [ $status -eq 0 ]; then
  echo
  echo "every regression test was proven red without its fix"
else
  echo
  echo "at least one regression test was NOT proven red"
fi
exit $status
