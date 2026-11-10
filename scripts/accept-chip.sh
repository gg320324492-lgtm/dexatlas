#!/usr/bin/env bash
# Accept one branch and merge it into main.
#
#   accept-chip.sh <branch> [<test-file>:<description> ...]
#
# The order matters and is the acceptance order:
#
#   1. merge the branch
#   2. remap the citations the merge moved -- the checker resolves a citation
#      by the symbol the sentence names, and the remapper follows that symbol
#      to where it lives now, so the line numbers are re-derived rather than
#      guessed at
#   3. add the rows for the new test files to the report's hand-written table
#   4. re-measure the figures: the fingerprint covers src/ and tests/, so the
#      report is stale the moment the tree changes
#   5. run the gates
#   6. re-run the two document checkers
#
# It stops before the commit: the merge, the remapping and the new rows are
# all things a reviewer wants to read, and the commit is where they become
# permanent.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
REPORT="$REPO/docs/reports/phase1-execution-report.md"

BRANCH="${1:?usage: accept-chip.sh <branch> [test-file:description ...]}"
shift

cd "$REPO"

echo "### merging $BRANCH ###"
git merge --no-ff --no-edit "$BRANCH"
MERGED=$(git rev-parse HEAD)
echo "### merged: $MERGED"

echo "### remapping the citations ###"
uv run --no-sync python scripts/remap-citations.py

echo "### the report's test-file table ###"
for entry in "$@"; do
  file="${entry%%:*}"
  description="${entry#*:}"
  if grep -q "| \`$file\` |" "$REPORT"; then
    echo "  $file is already in the table"
    continue
  fi
  python - "$REPORT" "$file" "$description" <<'PY'
import sys

report, name, description = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(report, encoding="utf-8").read()
row = f"| `{name}` | {description} |"
# The table ends at the last row before the next heading.
section = text.split("### 2.1", 1)[-1].split("\n### ", 1)[0]
lines = section.split("\n")
last = max(i for i, line in enumerate(lines) if line.startswith("| `"))
lines.insert(last + 1, row)
new_section = "\n".join(lines)
text = text.replace(section, new_section, 1)
open(report, "w", encoding="utf-8", newline="").write(text)
print(f"  added {name}")
PY
done

echo "### re-measuring the figures ###"
# Before the gates, not after. The report's self-checks read the report's
# recorded measurement, and the fingerprint covers src/ and tests/ -- so the
# moment the merge lands, the report describes a tree that no longer exists
# and its own checks are red. The refresh is what makes them green again,
# and it needs the new test files already in the table to converge in one
# run. So: rows first, then the refresh, then the gates.
uv run --no-sync python scripts/refresh-report-figures.py \
  || echo "!!! the refresh did not converge -- read the output above before trusting the gates"

echo "### gates ###"
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync mypy

echo "### the citation checker ###"
uv run --no-sync python scripts/check-doc-citations.py

echo "### the full suite ###"
uv run --no-sync pytest -q -p no:cacheprovider

echo "### the checkers, again ###"
uv run --no-sync python scripts/check-doc-citations.py
uv run --no-sync python scripts/check-version-claims.py --base auto

echo
echo "### ready to review ###"
git status --short
git log --oneline -3
echo "Nothing is committed yet. Read the diff, then commit and push."
