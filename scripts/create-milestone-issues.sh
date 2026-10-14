#!/usr/bin/env bash
# Create the Phase 1 milestone issues on the remote repository.
#
# Issue bodies live here rather than being typed at the CLI so they can be reviewed and
# edited as files. Re-running is safe-ish: it will fail on duplicate titles, which is
# the signal to stop and look rather than to force duplicates.

set -euo pipefail

REPO="${REPO:-gg320324492-lgtm/dexatlas}"
MILESTONE="${MILESTONE:-v0.1.0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISSUE_DIR="${SCRIPT_DIR}/.github/issues/v0.1.0"

shopt -s nullglob
files=("${ISSUE_DIR}"/*.md)
if [[ ${#files[@]} -eq 0 ]]; then
  echo "No issue files found in ${ISSUE_DIR}"
  exit 1
fi

for file in "${files[@]}"; do
  title="$(head -1 "${file}" | sed 's/^# //')"
  echo "Creating: ${title}"
  gh issue create \
    --repo "${REPO}" \
    --title "${title}" \
    --body-file "${file}" \
    --milestone "${MILESTONE}"
done

echo
echo "Done. View: https://github.com/${REPO}/milestone/1"
