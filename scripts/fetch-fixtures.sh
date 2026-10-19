#!/usr/bin/env bash
# Fetch the third-party test APKs the integration suite runs against.
#
# These are NOT committed to the repository. A git clone should not carry binaries whose
# provenance a reader cannot check from the tree alone; this script records exactly where
# each one comes from and under what licence.
#
#   fixtures/apk/
#     TestActivity.apk  androguard/androguard @ tests/data/APK  (Apache-2.0)
#     multidex.apk      androguard/androguard @ tests/data/APK  (Apache-2.0)
#
# Only what a test actually reads. Two fixtures were fetched here and used by nothing
# until a check was added that keeps this list and the integration tests in step; a
# download nobody reads is a slow, invisible cost in every CI run.
#
# Run once before `pytest -m slow`. The suite skips any fixture that is absent, so this
# is optional for the fast test run.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${REPO_ROOT}/fixtures/apk"
SOURCE_REPO="androguard/androguard"
SOURCE_PATH="tests/data/APK"
SOURCE_REF="${SOURCE_REF:-master}"

FILES=(
  "TestActivity.apk"
  # Two dexes, so it exercises the smali/ + smali_classes2/ layout the Smali
  # fallback depends on. Without it that test silently skips everywhere except
  # a developer's machine, which is the worst outcome for a regression test.
  "multidex.apk"
)

mkdir -p "${DEST}"

for name in "${FILES[@]}"; do
  echo "Fetching ${name}..."
  gh api "repos/${SOURCE_REPO}/contents/${SOURCE_PATH}/${name}?ref=${SOURCE_REF}" \
    --jq '.content' | base64 -d > "${DEST}/${name}"
  printf '  %s (%s bytes)\n' "${name}" "$(wc -c < "${DEST}/${name}" | tr -d ' ')"
done

cat > "${DEST}/SOURCES.md" <<'EOF'
# Third-party test fixtures

These APKs are **not** part of DexAtlas source. They are analysis *inputs* for the
integration test suite, downloaded by `scripts/fetch-fixtures.sh`.

| File                      | Source                                                        | Licence     |
| ------------------------- | ------------------------------------------------------------- | ----------- |
| `TestActivity.apk`        | `androguard/androguard` @ `tests/data/APK`                   | Apache-2.0  |
| `multidex.apk`            | `androguard/androguard` @ `tests/data/APK`                   | Apache-2.0  |

All are self-contained test applications built by the androguard project for its own
tests. None contains third-party application code, credentials or user data.

`multidex.apk` carries two dexes. It is what makes the Smali fallback test real:
Apktool decodes it to `smali/` and `smali_classes2/`, and the bug that test guards
against could only ever be caught by an APK with a second dex.

Any fixture added here must be either authored by this project or carry an explicit
licence permitting redistribution. See `CONTRIBUTING.md`.
EOF

echo
echo "Fixtures ready in ${DEST}"
