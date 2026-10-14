#!/usr/bin/env bash
# Create the Phase 1 tracking issues on the remote repository.
#
# Issue bodies live as files under .github/issues/ so they can be reviewed and edited
# like any other content. Files are named NNN-slug.md; the leading number orders them.

set -euo pipefail

REPO="${REPO:-gg320324492-lgtm/dexatlas}"
MILESTONE="${MILESTONE:-v0.1.0}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISSUE_DIR="${REPO_ROOT}/.github/issues/${MILESTONE}"

shopt -s nullglob
files=("${ISSUE_DIR}"/*.md)
if [[ ${#files[@]} -eq 0 ]]; then
  echo "No issue files found in ${ISSUE_DIR}"
  exit 1
fi
for file in "${files[@]}"; do
  title="$(head -1 "${file}" | sed 's/^# //')"
  if [[ -z "${title}" ]]; then
    echo "Skipping ${file##*/}: no title on the first line" >&2
    continue
  fi

  # A file that exists and whose issue is already closed should not be reopened by a
  # re-run; check before creating so a repeat run does not duplicate the backlog.
  existing="$(gh issue list --repo "${REPO}" --state all --search "${title} in:title" \
    --json number,title --jq '.[0].number // empty' 2>/dev/null || true)"
  if [[ -n "${existing}" ]]; then
    echo "Skipping (issue #${existing} exists): ${title}"
    continue
  fi

  echo "Creating: ${title}"
  gh issue create \
    --repo "${REPO}" \
    --title "${title}" \
    --body-file "${file}" \
    --milestone "${MILESTONE}"
done

echo
echo "Done. View: https://github.com/${REPO}/milestone/1"
